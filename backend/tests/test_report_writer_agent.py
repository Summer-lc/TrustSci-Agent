from app.agents.report_writer_agent import ReportWriterAgent
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import CriticReview, Hypothesis
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


def test_report_writer_uses_only_verified_references() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid electrolyte research plan.",
        constraints=ResearchConstraints(max_papers=3),
    )
    verified = Paper(
        paper_id="p_verified",
        title="Verified solid electrolyte paper",
        year=2024,
        doi="10.1234/verified",
        verification_status="verified",
        verified_by=["openalex", "crossref"],
        report_eligible=True,
    )
    rejected = Paper(
        paper_id="p_rejected",
        title="Rejected paper",
        year=2022,
        doi="10.1234/rejected",
        verification_status="rejected",
        verified_by=["openalex"],
    )
    report = ReportWriterAgent().run(
        run,
        _hypothesis(),
        _experiment(),
        [_evidence()],
        [verified, rejected],
        [_data_profile()],
        _baseline_card(),
    )

    assert report.references == [verified]
    assert "Rejected paper" not in [paper.title for paper in report.references]
    assert any("p_rejected: rejected" in line for line in report.citation_audit_log)
    assert "baseline result card" in report.results
    assert report.paper_abstract
    assert report.technical_details


def test_report_writer_marks_results_pending_without_verified_inputs() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Plan a bounded materials hypothesis.",
        constraints=ResearchConstraints(max_papers=1),
    )
    unverified = Paper(
        paper_id="p_unverified",
        title="Unverified paper",
        verification_status="candidate",
    )
    report = ReportWriterAgent().run(
        run,
        None,
        _experiment(),
        [],
        [unverified],
        [],
        None,
    )

    assert report.references == []
    assert "verification pending" in report.problem_statement
    assert "verification pending" in report.results
    assert any("p_unverified: candidate" in line for line in report.citation_audit_log)


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        hypothesis_id="h1",
        statement="Aliovalent substitution may improve ion transport while preserving stability.",
        rationale="A bounded mechanism hypothesis for the MVP.",
        supporting_evidence=["e1"],
        novelty_claim="Combines evidence ledger constraints with a measurable validation path.",
        verification_path="Compare baseline and feature-aware models on a Matbench-compatible target.",
        critic=CriticReview(
            novelty=7,
            self_consistency=8,
            verifiability=8,
            data_availability=7,
            risk="Dataset may not isolate causal mechanisms.",
            revision_advice="Keep claims bounded to measurable associations.",
        ),
    )


def _experiment() -> ExperimentPlan:
    return ExperimentPlan(
        datasets=["bundled_solid_electrolyte_candidates"],
        source="Materials Project / Matbench profile",
        target="ionic_conductivity_proxy",
        baselines=["mean_baseline"],
        metrics=["MAE", "RMSE"],
        experiment_steps=["Load profile", "Run baseline", "Create result card"],
        expected_results="Expected improvement must be validated by a real benchmark run.",
        failure_modes=["Sparse data", "Unverified mechanism labels"],
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


def _data_profile() -> DatasetProfile:
    return DatasetProfile(
        name="bundled_solid_electrolyte_candidates",
        source="local fixture",
        rows=12,
        fields=["formula", "ionic_conductivity_proxy"],
        target="ionic_conductivity_proxy",
        task_type="regression",
    )


def _baseline_card() -> BaselineResultCard:
    return BaselineResultCard(
        name="solid_electrolyte_mean_baseline",
        dataset="bundled_solid_electrolyte_candidates",
        target="ionic_conductivity_proxy",
        model="mean_baseline",
        train_rows=8,
        test_rows=4,
        metrics={"mae": 0.12},
        result_summary="Toy baseline completed.",
    )
