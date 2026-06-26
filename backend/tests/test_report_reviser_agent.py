from app.agents.report_reviser_agent import ReportReviserAgent
from app.agents.report_writer_agent import ReportWriterAgent
from app.schemas.claim import ClaimAuditItem, ClaimAuditReport
from app.schemas.evidence import EvidenceItem
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


def test_report_reviser_layers_and_downgrades_flagged_claims() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a bounded solid-state electrolyte research plan.",
        constraints=ResearchConstraints(max_papers=1),
    )
    paper = Paper(
        paper_id="p1",
        title="Verified solid electrolyte study",
        verification_status="verified",
        report_eligible=True,
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_001",
            paper_id="p1",
            claim="Solid electrolyte stability is constrained by interfacial degradation.",
            quote_or_summary="Verified evidence describes interfacial degradation in solid electrolytes.",
            source_title="Verified solid electrolyte study",
            verified=True,
            eligible_for_report=True,
        )
    ]
    report = ReportWriterAgent().run(
        run,
        Hypothesis(
            hypothesis_id="H1",
            statement="Dynamic pressure may mitigate delamination.",
            rationale="A bounded hypothesis.",
            supporting_evidence=["ev_001"],
            novelty_claim="A testable pressure-control hypothesis.",
            verification_path="Run controlled pressure experiments.",
        ),
        ExperimentPlan(
            datasets=["to be collected: operando pressure-cell data"],
            source="verified literature evidence",
            target="interfacial resistance and capacity retention",
            baselines=["static pressure"],
            metrics=["capacity retention"],
            experiment_steps=["cycle under static and dynamic pressure"],
            expected_results="Dynamic pressure may improve retention.",
            failure_modes=["cell fracture"],
        ),
        evidence,
        [paper],
        [],
        [],
        None,
    )
    audit = ClaimAuditReport(
        total=2,
        supported=1,
        weakly_supported=0,
        unsupported=1,
        support_score=0.5,
        items=[
            ClaimAuditItem(
                claim_id="claim_001",
                claim="Interfacial degradation is reported.",
                status="supported",
                confidence=0.9,
                matched_evidence_ids=["ev_001"],
            ),
            ClaimAuditItem(
                claim_id="claim_002",
                claim="Dynamic pressure has already improved retention.",
                status="unsupported",
                confidence=0.0,
                matched_evidence_ids=[],
            ),
        ],
    )

    revised = ReportReviserAgent().run(run, report, audit, evidence, [paper], [])

    assert revised.references == [paper]
    assert "Evidence-backed:" in revised.rationale
    assert "Inference:" in revised.rationale
    assert "To validate:" in revised.rationale
    assert "claim_002=unsupported" in revised.results
