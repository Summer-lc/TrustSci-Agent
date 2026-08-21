import pytest

from app.config import Settings
from app.schemas.experiment_assistance import ExperimentAssistanceInput, MetricObservation
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow
from app.workflows.langgraph_workflow import LangGraphWorkflow


@pytest.mark.asyncio
async def test_experiment_assistance_analysis_does_not_execute_generated_code(monkeypatch) -> None:
    workflow = ScientistWorkflow(Settings(dashscope_api_key=""))
    run = ResearchRun(domain="seismic_event_classification", question="q", mode="experiment_assistance",
        constraints=ResearchConstraints(), experiment_assistance=ExperimentAssistanceInput(
            objective="Compare", method_summary="FFT model",
            baseline_metrics=[MetricObservation(name="accuracy", value=0.8)],
            method_metrics=[MetricObservation(name="accuracy", value=0.86)]))

    async def forbidden(*args, **kwargs):
        raise AssertionError("generated code path must be skipped")

    monkeypatch.setattr(workflow, "_run_code_experiment", forbidden)
    monkeypatch.setattr(workflow, "_run_macro_react", forbidden)
    await workflow._evaluate_results(run)
    await workflow._analyze_ablations(run)
    await workflow._interpret_results(run)
    assert run.result_evaluation.verdict == "pass"
    assert run.result_interpretation.evidence_boundary


@pytest.mark.asyncio
async def test_langgraph_assistance_route_reaches_result_analysis(monkeypatch) -> None:
    async def noop(self, run):
        return None
    for name in ("_route_intent", "_plan", "_search_literature_with_langchain_tools",
                 "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
                 "_profile_scientific_data", "_write_report", "_verify_claims",
                 "_revise_report_after_audit", "_translate_report"):
        monkeypatch.setattr(LangGraphWorkflow, name, noop)
    workflow = LangGraphWorkflow(Settings(dashscope_api_key="", workflow_engine="langgraph"))
    run = ResearchRun(domain="seismic_event_classification", question="q", mode="experiment_assistance",
        constraints=ResearchConstraints(), experiment_assistance=ExperimentAssistanceInput(
            objective="Compare", method_summary="FFT model",
            baseline_metrics=[MetricObservation(name="accuracy", value=0.8)],
            method_metrics=[MetricObservation(name="accuracy", value=0.86)]))
    await workflow.run(run)
    assert run.status == "completed"
    assert run.result_evaluation.verdict == "pass"
    assert "code_experiment" not in [step.name for step in run.steps]
