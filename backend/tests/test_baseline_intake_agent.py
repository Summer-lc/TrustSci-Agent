import pytest

from app.agents.baseline_intake_agent import BaselineIntakeAgent
from app.config import Settings
from app.schemas.baseline_intake import BaselineIntakeRequest, ManualBaselineInput, MetricObservation
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


@pytest.mark.asyncio
async def test_agent_normalizes_manual_baseline() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="manual_upload",
        manual_baseline=BaselineIntakeRequest(
            strategy="manual_upload",
            manual=ManualBaselineInput(
                name="User baseline",
                description="Manual baseline.",
                metrics=[MetricObservation(name="accuracy", value=0.82)],
            ),
        ),
    )
    intake = await BaselineIntakeAgent().arun(run)
    assert intake.source_type == "manual_upload"
    assert intake.trust_level == "user_provided"
    assert intake.metrics[0].value == 0.82


@pytest.mark.asyncio
async def test_agent_creates_ai_generated_demo_baseline() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="ai_generated",
    )
    intake = await BaselineIntakeAgent().arun(run)
    assert intake.source_type == "ai_generated"
    assert intake.trust_level == "runnable_demo"
    assert "not an externally verified" in " ".join(intake.limitations).lower()


@pytest.mark.asyncio
async def test_agent_marks_no_baseline_as_insufficient() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="none",
    )
    intake = await BaselineIntakeAgent().arun(run)
    assert intake.source_type == "unavailable"
    assert intake.trust_level == "insufficient"


@pytest.mark.asyncio
async def test_baseline_gate_prefers_intake() -> None:
    workflow = ScientistWorkflow(Settings())
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="ai_generated",
    )
    run.baseline_intake = await BaselineIntakeAgent().arun(run)
    await workflow._evaluate_baseline_gate(run)
    assert run.baseline_gate_status is not None
    assert run.baseline_gate_status.run_gate_passed is True
    assert run.baseline_gate_status.research_gate_passed is False
    assert run.baseline_gate_status.comparison_grade == "degraded"
