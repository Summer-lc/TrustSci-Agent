from app.agents.report_writer_agent import _system_provenance
from app.schemas.baseline_intake import BaselineIntake, MetricObservation as BaselineMetricObservation
from app.schemas.experiment_assistance import AblationAnalysis, ExperimentAssistanceInput, MetricObservation, ResultEvaluation
from app.schemas.run import ResearchConstraints, ResearchRun


def test_assistance_provenance_labels_user_supplied_results() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q", mode="experiment_assistance",
        constraints=ResearchConstraints(), experiment_assistance=ExperimentAssistanceInput(
            objective="Compare", method_summary="FFT", baseline_name="LR",
            method_metrics=[MetricObservation(name="accuracy", value=0.86)]),
        result_evaluation=ResultEvaluation(verdict="pass"),
        ablation_analysis=AblationAnalysis(coverage="partial"))
    provenance = _system_provenance(run, [], [], [])
    assert provenance.baseline_provenance["source"] == "user-provided"
    assert provenance.ablation_report["coverage"] == "partial"
    assert provenance.result_support_judgment["verdict"] == "pass"


def test_report_provenance_prefers_baseline_intake() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="manual_upload",
        baseline_intake=BaselineIntake(
            strategy="manual_upload",
            source_type="manual_upload",
            trust_level="user_provided",
            name="User baseline",
            description="Manual baseline.",
            metrics=[BaselineMetricObservation(name="accuracy", value=0.8)],
            limitations=["manual limitation"],
            provenance_notes=["attached before start"],
        ),
    )
    provenance = _system_provenance(run, [], [], [])
    assert provenance.baseline_provenance["source_type"] == "manual_upload"
    assert provenance.baseline_provenance["trust_level"] == "user_provided"
    assert provenance.baseline_provenance["limitations"] == ["manual limitation"]
