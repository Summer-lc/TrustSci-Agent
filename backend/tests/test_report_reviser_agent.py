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
    assert revised.english_report is not None
    assert revised.chinese_report is None
    assert "unsupported claims" in revised.english_report.limitations_and_risk_controls
    assert revised.system_provenance is not None


def test_report_reviser_preserves_english_source_before_translation() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1),
    )
    paper = Paper(
        paper_id="p1",
        title="Li-Solid Electrolyte Interfaces/Interphases in All-Solid-State Li Batteries",
        verification_status="verified",
        report_eligible=True,
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_001",
            paper_id="p1",
            claim=(
                "Solid-state electrolyte literature links structure, transport pathways, "
                "and stability constraints."
            ),
            quote_or_summary=(
                "Furthermore, effective methodologies aimed at enhancing anode interfacial "
                "stability include SEI interlayer insertion and SE optimization."
            ),
            source_title="Li-Solid Electrolyte Interfaces/Interphases in All-Solid-State Li Batteries",
            verified=True,
            eligible_for_report=True,
        )
    ]
    hypothesis = Hypothesis(
        hypothesis_id="H1",
        statement=(
            "Zr and Mo co-doping in Li7TaO6 selectively segregates to grain boundaries, "
            "reducing the local activation barrier for Li-ion transport and closing the gap "
            "between simulated bulk conductivity and experimental total conductivity."
        ),
        rationale="A bounded hypothesis.",
        supporting_evidence=["ev_001"],
        novelty_claim="A testable co-doping hypothesis.",
        verification_path="Run DFT, AIMD, EIS, STEM-EDS, and EBSD validation.",
        selected=True,
    )
    experiment = ExperimentPlan(
        datasets=["planned synthesis and characterization dataset"],
        source="historical reports, migrated metadata, local solid electrolyte candidates, Matbench, and Materials Project availability",
        target="samples under synthesis conditions, XRD phase purity, SEM/EBSD grain size, EIS resistance, and XPS descriptors",
        baselines=["Undoped Li7TaO6 (bulk and grain boundary)", "Zr or Mo single-doped Li7TaO6"],
        metrics=[
            "Segregation energy (eV)",
            "Activation energy for Li migration (eV)",
            "Ionic conductivity (S/cm)",
            "Grain boundary resistance (Ohm*cm^2)",
        ],
        experiment_steps=[
            "To validate: Method: Density Functional Theory (DFT) with Nudged Elastic Band (NEB)",
            "To validate: Method: Electrochemical Impedance Spectroscopy (EIS)",
            "To validate: Method: Scanning Transmission Electron Microscopy (STEM-EDS) and EBSD",
        ],
        expected_results=(
            "To validate: Bounded expectation: Simulations will yield negative segregation energies "
            "for Zr/Mo at GBs and a reduced GB Li-migration barrier."
        ),
        failure_modes=["secondary phase precipitation"],
    )
    run.hypotheses = [hypothesis]
    report = ReportWriterAgent().run(run, hypothesis, experiment, evidence, [paper], [], [], None)
    audit = ClaimAuditReport(
        total=1,
        supported=1,
        weakly_supported=0,
        unsupported=0,
        support_score=1.0,
        items=[
            ClaimAuditItem(
                claim_id="claim_001",
                claim="Solid electrolyte literature links structure and transport pathways.",
                status="supported",
                confidence=0.9,
                matched_evidence_ids=["ev_001"],
            )
        ],
    )

    revised = ReportReviserAgent().run(run, report, audit, evidence, [paper], [])

    assert revised.english_report is not None
    assert revised.chinese_report is None
    english_text = _formal_report_text(revised.english_report)
    assert "Controlled material groups" in english_text or "controlled" in english_text.lower()
    assert "Report Translator" not in english_text


def _formal_report_text(report) -> str:
    return "\n".join(
        [
            report.paper_title,
            report.paper_abstract,
            report.problem_statement,
            report.rationale,
            report.technical_details,
            report.datasets.source,
            report.datasets.target,
            report.methods,
            report.experiments.baselines,
            report.experiments.metrics,
            report.experiments.design,
            report.results.executed_results,
            report.results.expected_validation_outcomes,
            report.limitations_and_risk_controls,
        ]
    )
