import pytest

from app.agents.result_analysis_agents import AblationAgent, ResultEvaluatorAgent, ResultInterpreterAgent
from app.config import Settings
from app.llm.registry import build_llm_client
from app.schemas.experiment_assistance import AblationObservation, ExperimentAssistanceInput, MetricObservation
from app.schemas.run import ResearchConstraints, ResearchRun


def _run() -> ResearchRun:
    return ResearchRun(domain="seismic_event_classification", question="q", mode="experiment_assistance",
        constraints=ResearchConstraints(), experiment_assistance=ExperimentAssistanceInput(
            objective="Beat baseline", method_summary="FFT random forest", baseline_name="LR",
            baseline_metrics=[MetricObservation(name="accuracy", value=0.8)],
            method_metrics=[MetricObservation(name="accuracy", value=0.86)],
            ablations=[AblationObservation(component="FFT", metrics=[MetricObservation(name="accuracy", value=0.75)])]))


@pytest.mark.asyncio
async def test_result_agents_produce_bounded_deterministic_analysis() -> None:
    run = _run()
    llm = build_llm_client(Settings(dashscope_api_key=""))
    run.result_evaluation = await ResultEvaluatorAgent(llm).arun(run)
    run.ablation_analysis = await AblationAgent(llm).arun(run)
    run.result_interpretation = await ResultInterpreterAgent(llm).arun(run)
    assert run.result_evaluation.verdict == "pass"
    assert run.result_evaluation.metric_deltas[0].delta == pytest.approx(0.06)
    assert run.ablation_analysis.coverage == "partial"
    assert "user-provided" in run.result_interpretation.evidence_boundary.lower()
