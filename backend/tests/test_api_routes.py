import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import CriticReview, Hypothesis
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.in_memory import run_store


client = TestClient(app)


def test_system_health_and_config() -> None:
    health = client.get("/api/system/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    config = client.get("/api/system/config")
    assert config.status_code == 200
    assert "qwen_model" in config.json()
    assert "browser_worker_url" in config.json()
    assert "semantic_scholar_configured" in config.json()
    assert config.json()["arxiv_available"] is True


def test_data_profiles_and_baseline() -> None:
    profiles = client.get("/api/data/profiles")
    assert profiles.status_code == 200
    assert any(item["name"] == "bundled_solid_electrolyte_candidates" for item in profiles.json())

    baseline = client.post("/api/data/baseline")
    assert baseline.status_code == 200
    assert baseline.json()["name"] == "solid_electrolyte_mean_baseline"


def test_run_detail_endpoints_before_execution() -> None:
    payload = {
        "domain": "energy_materials",
        "question": "Generate a test hypothesis.",
        "constraints": {"max_papers": 1, "enable_semantic_scholar": True, "enable_arxiv": False},
    }
    created = client.post("/api/runs", json=payload)
    assert created.status_code == 200
    assert created.json()["constraints"]["enable_semantic_scholar"] is True
    assert created.json()["constraints"]["enable_arxiv"] is False
    assert created.json()["workspace_path"]
    assert "research_state" in created.json()["workspace_artifacts"]
    run_id = created.json()["run_id"]

    assert client.get(f"/api/runs/{run_id}/papers").json() == []
    assert client.get(f"/api/runs/{run_id}/evidence").json() == []
    assert client.get(f"/api/runs/{run_id}/perspectives").json() == []
    assert client.get(f"/api/runs/{run_id}/knowledge-cards").json() == []
    assert client.get(f"/api/runs/{run_id}/paper-chunks").json() == []
    assert client.get(f"/api/runs/{run_id}/claim-audit").json() is None
    assert client.get(f"/api/runs/{run_id}/hypotheses").json() == []
    assert client.get(f"/api/runs/{run_id}/llm-calls").json() == []
    assert client.get(f"/api/runs/{run_id}/report").status_code == 404

    artifacts = client.get(f"/api/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    assert any(path.endswith("research-state.json") for path in artifacts.json()["artifacts"]["workspace"])

    workspace_zip = client.get(f"/api/runs/{run_id}/workspace/export")
    assert workspace_zip.status_code == 200
    assert workspace_zip.content[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(workspace_zip.content)) as archive:
        names = set(archive.namelist())
    assert f"{run_id}/research-state.json" in names
    assert f"{run_id}/to_human/next-actions.md" in names

    run_store.delete(run_id)
    assert client.get(f"/api/runs/{run_id}").status_code == 404

    workspaces = client.get("/api/runs/workspaces")
    assert workspaces.status_code == 200
    assert any(item["run_id"] == run_id for item in workspaces.json())

    restored = client.post(f"/api/runs/{run_id}/workspace/restore")
    assert restored.status_code == 200
    assert restored.json()["run_id"] == run_id
    assert restored.json()["question"] == payload["question"]
    assert "research_state" in restored.json()["workspace_artifacts"]
    assert client.get(f"/api/runs/{run_id}").status_code == 200


def test_pdf_evidence_ingest_endpoint_accepts_data_dir_pdf() -> None:
    payload = {
        "domain": "energy_materials",
        "question": "Generate a test hypothesis.",
        "constraints": {"max_papers": 1},
    }
    created = client.post("/api/runs", json=payload)
    run_id = created.json()["run_id"]

    pdf_path = Path("data/test_blank_ingest.pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as handle:
        writer.write(handle)

    response = client.post(f"/api/runs/{run_id}/pdf-evidence", json={"pdf_path": str(pdf_path)})

    assert response.status_code == 200
    assert response.json()["paper_chunks"] == []

    pdf_path.unlink(missing_ok=True)


def test_pdf_evidence_ingest_rejects_paths_outside_data_dir() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "energy_materials", "question": "Generate a test hypothesis."},
    )
    run_id = created.json()["run_id"]

    response = client.post(f"/api/runs/{run_id}/pdf-evidence", json={"pdf_path": "/tmp/not_allowed.pdf"})

    assert response.status_code == 400


def test_evidence_decision_and_freeze_restrict_report_set() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Freeze evidence before final report.",
        constraints=ResearchConstraints(max_papers=2),
    )
    run.papers = [
        Paper(
            paper_id="p_keep",
            title="Kept verified paper",
            verification_status="verified",
            report_eligible=True,
        ),
        Paper(
            paper_id="p_reject",
            title="Rejected verified paper",
            verification_status="verified",
            report_eligible=True,
        ),
    ]
    run.evidence = [
        EvidenceItem(
            evidence_id="ev_keep",
            paper_id="p_keep",
            claim="Kept evidence supports the research plan.",
            source_title="Kept verified paper",
            quote_or_summary="Traceable support.",
            verified=True,
            eligible_for_report=True,
        ),
        EvidenceItem(
            evidence_id="ev_reject",
            paper_id="p_reject",
            claim="Rejected evidence should not enter the report.",
            source_title="Rejected verified paper",
            quote_or_summary="Rejected support.",
            verified=True,
            eligible_for_report=True,
        ),
    ]
    run.experiment_plan = ExperimentPlan(
        datasets=["fixture"],
        source="local",
        target="target",
        baselines=["mean"],
        metrics=["MAE"],
        experiment_steps=["freeze evidence", "write report"],
        expected_results="bounded",
        failure_modes=["weak evidence"],
    )
    run_store.create(run)

    rejected = client.post(
        f"/api/runs/{run.run_id}/evidence/ev_reject/decision",
        json={"decision": "rejected", "note": "not enough support"},
    )
    assert rejected.status_code == 200
    rejected_item = next(item for item in rejected.json()["evidence"] if item["evidence_id"] == "ev_reject")
    assert rejected_item["human_decision"] == "rejected"
    assert rejected_item["eligible_for_report"] is False

    frozen = client.post(f"/api/runs/{run.run_id}/evidence/freeze")

    assert frozen.status_code == 200
    body = frozen.json()
    assert body["evidence_frozen"] is True
    assert body["frozen_evidence_ids"] == ["ev_keep"]
    assert body["frozen_paper_ids"] == ["p_keep"]
    assert [paper["paper_id"] for paper in body["report"]["references"]] == ["p_keep"]
    assert body["claim_audit"]["total"] > 0


def test_paper_decision_and_freeze_restrict_citation_set() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Freeze citations before final report.",
        constraints=ResearchConstraints(max_papers=2),
    )
    run.papers = [
        Paper(
            paper_id="p_keep",
            title="Kept citation",
            verification_status="verified",
            report_eligible=True,
        ),
        Paper(
            paper_id="p_reject",
            title="Rejected citation",
            verification_status="verified",
            report_eligible=True,
        ),
    ]
    run.evidence = [
        EvidenceItem(
            evidence_id="ev_keep",
            paper_id="p_keep",
            claim="Kept citation evidence supports the report.",
            source_title="Kept citation",
            quote_or_summary="Traceable support.",
            verified=True,
            eligible_for_report=True,
        ),
        EvidenceItem(
            evidence_id="ev_reject",
            paper_id="p_reject",
            claim="Rejected citation evidence should not support the report.",
            source_title="Rejected citation",
            quote_or_summary="Rejected support.",
            verified=True,
            eligible_for_report=True,
        ),
    ]
    run.experiment_plan = ExperimentPlan(
        datasets=["fixture"],
        source="local",
        target="target",
        baselines=["mean"],
        metrics=["MAE"],
        experiment_steps=["freeze citations", "write report"],
        expected_results="bounded",
        failure_modes=["weak citation"],
    )
    run_store.create(run)

    rejected = client.post(
        f"/api/runs/{run.run_id}/papers/p_reject/decision",
        json={"decision": "rejected", "note": "citation is out of scope"},
    )
    assert rejected.status_code == 200
    rejected_paper = next(item for item in rejected.json()["papers"] if item["paper_id"] == "p_reject")
    rejected_evidence = next(item for item in rejected.json()["evidence"] if item["evidence_id"] == "ev_reject")
    assert rejected_paper["human_decision"] == "rejected"
    assert rejected_paper["report_eligible"] is False
    assert rejected_evidence["eligible_for_report"] is False

    frozen = client.post(f"/api/runs/{run.run_id}/papers/freeze")

    assert frozen.status_code == 200
    body = frozen.json()
    assert body["citation_frozen"] is True
    assert body["frozen_paper_ids"] == ["p_keep"]
    assert [paper["paper_id"] for paper in body["report"]["references"]] == ["p_keep"]
    assert body["papers"][0]["frozen"] is True


def test_select_hypothesis_rebuilds_experiment_and_report() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Pick a hypothesis for final report.",
        constraints=ResearchConstraints(max_papers=1),
    )
    run.hypotheses = [
        Hypothesis(
            hypothesis_id="H1",
            statement="First candidate.",
            rationale="Initial candidate.",
            novelty_claim="Novel process.",
            verification_path="Run a baseline.",
            selected=True,
            critic=_critic(),
        ),
        Hypothesis(
            hypothesis_id="H2",
            statement="Second candidate with better evidence support.",
            rationale="Better candidate.",
            novelty_claim="Better bounded process.",
            verification_path="Run a better baseline.",
            critic=_critic(evidence_support=9),
        ),
    ]
    run_store.create(run)

    response = client.post(f"/api/runs/{run.run_id}/hypotheses/H2/select")

    assert response.status_code == 200
    body = response.json()
    selected = [item for item in body["hypotheses"] if item["selected"]]
    assert [item["hypothesis_id"] for item in selected] == ["H2"]
    assert selected[0]["selection_rationale"]
    assert "Second candidate" in body["experiment_plan"]["expected_results"]
    assert body["report"]["paper_title"].startswith("Evidence-Grounded Research Plan: Second candidate")
    assert body["claim_audit"]["total"] > 0

    markdown = client.get(f"/api/runs/{run.run_id}/report/export?format=md")
    assert markdown.status_code == 200
    assert markdown.text.startswith("# Evidence-Grounded Research Plan")

    pdf = client.get(f"/api/runs/{run.run_id}/report/export?format=pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def _critic(evidence_support: int = 7) -> CriticReview:
    return CriticReview(
        novelty=7,
        self_consistency=8,
        verifiability=8,
        data_availability=8,
        evidence_support=evidence_support,
        risk="Needs bounded claims.",
        revision_advice="Keep it testable.",
    )
