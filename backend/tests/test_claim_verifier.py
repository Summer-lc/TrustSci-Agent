from app.agents.report_writer_agent import ReportWriterAgent
from app.schemas.data import BaselineResultCard
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.run import ResearchConstraints, ResearchRun
from app.tools.claim_verifier import ClaimVerifier


def test_claim_verifier_audits_report_against_eligible_evidence() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a solid electrolyte conductivity research plan.",
        constraints=ResearchConstraints(max_papers=1),
    )
    hypothesis = Hypothesis(
        hypothesis_id="H1",
        statement="Solid electrolyte structure descriptors can support ionic conductivity prioritization.",
        rationale="A bounded MVP hypothesis.",
        supporting_evidence=["ev_001"],
        novelty_claim="Traceable evidence workflow.",
        verification_path="Compare baseline metrics.",
    )
    experiment = ExperimentPlan(
        datasets=["solid_electrolyte_candidates"],
        source="Materials profile",
        target="ionic conductivity",
        baselines=["mean_baseline"],
        metrics=["MAE"],
        experiment_steps=["Load data", "Run baseline"],
        expected_results="Expected improvement must be verified.",
        failure_modes=["Sparse labels"],
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_001",
            claim="Solid electrolyte structure descriptors connect to ionic conductivity prioritization.",
            source_title="Verified paper",
            quote_or_summary="The paper links solid electrolyte structure descriptors and ionic conductivity.",
            verified=True,
            eligible_for_report=True,
        )
    ]
    report = ReportWriterAgent().run(
        run,
        hypothesis,
        experiment,
        evidence,
        [],
        [],
        [],
        BaselineResultCard(
            name="mean_baseline",
            dataset="solid_electrolyte_candidates",
            target="ionic conductivity",
            model="mean",
            train_rows=4,
            test_rows=2,
            metrics={"MAE": 1.0},
            result_summary="small baseline",
        ),
    )

    audit = ClaimVerifier().audit(run, report, evidence, hypothesis)

    assert audit.total > 0
    assert audit.supported >= 1
    assert audit.support_score > 0
    assert any("ev_001" in item.matched_evidence_ids for item in audit.items)


def test_claim_verifier_marks_claims_unsupported_without_eligible_evidence() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a battery materials plan.",
        constraints=ResearchConstraints(max_papers=1),
    )
    experiment = ExperimentPlan(
        datasets=["none"],
        source="none",
        target="none",
        baselines=[],
        metrics=[],
        experiment_steps=[],
        expected_results="none",
        failure_modes=[],
    )
    report = ReportWriterAgent().run(run, None, experiment, [], [], [], [], None)

    audit = ClaimVerifier().audit(run, report, [], None)

    assert audit.total > 0
    assert audit.unsupported > 0
    assert any(item.status == "unsupported" for item in audit.items)
