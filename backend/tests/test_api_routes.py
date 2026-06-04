from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
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
