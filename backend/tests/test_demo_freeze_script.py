import importlib.util
from pathlib import Path

from app.agents.report_writer_agent import ReportWriterAgent
from app.schemas.claim import ClaimAuditReport
from app.schemas.citation import CitationVerificationReport
from app.schemas.common import RunStatus
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import CriticReview, Hypothesis
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.workspace import RunWorkspace


def test_freeze_demo_case_generates_submission_package(tmp_path: Path) -> None:
    module = _load_freeze_script()
    data_dir = tmp_path / "data"
    output_root = tmp_path / "submission"
    run = _demo_run()
    RunWorkspace(data_dir).write_snapshot(run)
    llm_log = data_dir / "outputs" / "llm_calls" / f"{run.run_id}.jsonl"
    llm_log.parent.mkdir(parents=True, exist_ok=True)
    llm_log.write_text('{"model":"qwen-plus","prompt_tokens":12,"completion_tokens":8}\n', encoding="utf-8")

    manifest = module.freeze_demo_case(run.run_id, data_dir, output_root)
    package_dir = output_root / run.run_id

    assert manifest["run_id"] == run.run_id
    assert manifest["warnings"] == []
    assert manifest["checks"]["references_within_frozen_papers"] is True
    assert (package_dir / "manifest.json").exists()
    assert (package_dir / "README.md").exists()
    assert (package_dir / manifest["artifacts"]["report_markdown"]).exists()
    assert (package_dir / manifest["artifacts"]["report_json"]).exists()
    assert (package_dir / manifest["artifacts"]["report_pdf"]).read_bytes().startswith(b"%PDF")
    assert (package_dir / manifest["artifacts"]["workspace_bundle"]).read_bytes().startswith(b"PK")
    assert (package_dir / manifest["artifacts"]["qwen_llm_log"]).exists()


def _load_freeze_script():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "freeze_demo_case.py"
    spec = importlib.util.spec_from_file_location("freeze_demo_case", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _demo_run() -> ResearchRun:
    run = ResearchRun(
        run_id="run_demo_freeze",
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte research plan.",
        constraints=ResearchConstraints(max_papers=1),
        status=RunStatus.completed,
        current_stage="completed",
        progress=1.0,
        evidence_frozen=True,
        citation_frozen=True,
        frozen_evidence_ids=["e1"],
        frozen_paper_ids=["p_verified"],
    )
    run.papers = [_paper()]
    run.evidence = [_evidence()]
    run.knowledge_cards = [_knowledge_card()]
    run.hypotheses = [_hypothesis()]
    run.experiment_plan = _experiment()
    run.citation_report = CitationVerificationReport(total=1, verified=1, integrity_score=1.0)
    run.claim_audit = ClaimAuditReport(total=2, supported=2, support_score=1.0)
    run.report = ReportWriterAgent().run(
        run,
        run.hypotheses[0],
        run.experiment_plan,
        run.evidence,
        run.papers,
        run.knowledge_cards,
        [],
        None,
    )
    return run


def _paper() -> Paper:
    return Paper(
        paper_id="p_verified",
        title="Verified solid electrolyte paper",
        year=2024,
        doi="10.1234/demo",
        verification_status="verified",
        report_eligible=True,
    )


def _evidence() -> EvidenceItem:
    return EvidenceItem(
        evidence_id="e1",
        paper_id="p_verified",
        claim="Substitution can alter transport bottlenecks.",
        source_title="Verified solid electrolyte paper",
        quote_or_summary="A verified summary from the evidence ledger.",
        verified=True,
        eligible_for_report=True,
    )


def _knowledge_card() -> KnowledgeCard:
    return KnowledgeCard(
        card_id="kc_001",
        title="Verified solid electrolyte paper",
        perspective="domain_mechanism",
        finding="Substitution can alter transport bottlenecks.",
        evidence_ids=["e1"],
        paper_ids=["p_verified"],
        confidence=0.9,
        report_eligible=True,
    )


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        hypothesis_id="h1",
        statement="Aliovalent substitution may improve ion transport while preserving stability.",
        rationale="A bounded mechanism hypothesis.",
        supporting_evidence=["e1"],
        novelty_claim="Bounded and measurable.",
        verification_path="Run a Matbench-compatible baseline.",
        selected=True,
        selection_rationale="Selected for the frozen demo.",
        critic=CriticReview(
            novelty=7,
            self_consistency=8,
            verifiability=8,
            data_availability=8,
            evidence_support=8,
            reproducibility=8,
            competition_fit=8,
            risk="Needs more data.",
            revision_advice="Keep claims bounded.",
        ),
    )


def _experiment() -> ExperimentPlan:
    return ExperimentPlan(
        datasets=["bundled_solid_electrolyte_candidates"],
        source="local fixture",
        target="ionic_conductivity_proxy",
        baselines=["mean_baseline"],
        metrics=["MAE"],
        experiment_steps=["Load data", "Run baseline"],
        expected_results="Bounded improvement if validated.",
        failure_modes=["Sparse data"],
    )
