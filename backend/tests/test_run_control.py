import httpx
import pytest

from app.config import Settings
from app.schemas.common import AgentStep
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.run_control import classify_step_error
from app.workflows.scientist_workflow import ScientistWorkflow, StepNeedsAction


def test_agent_step_has_resilience_defaults() -> None:
    step = AgentStep(name="literature_search")

    assert step.attempts == 0
    assert step.retryable is False
    assert step.skippable is False
    assert step.error_code is None
    assert step.error_summary is None
    assert step.events == []


def test_old_run_snapshot_remains_valid() -> None:
    run = ResearchRun.model_validate(
        {
            "domain": "energy_materials",
            "question": "q",
            "constraints": ResearchConstraints().model_dump(),
            "steps": [
                {
                    "name": "planner",
                    "status": "completed",
                    "summary": "ok",
                }
            ],
        }
    )

    assert run.resume_count == 0
    assert run.trust_warnings == []
    assert run.last_action is None
    assert run.steps[0].attempts == 0


def test_network_error_is_retryable() -> None:
    decision = classify_step_error(httpx.ReadTimeout("late"), "literature_search")

    assert decision.code == "temporary_network_error"
    assert decision.retryable is True


def test_validation_error_is_not_retryable() -> None:
    decision = classify_step_error(ValueError("missing baseline"), "baseline_intake")

    assert decision.code == "step_validation_error"
    assert decision.retryable is False


@pytest.mark.asyncio
async def test_step_retries_once_then_completes() -> None:
    workflow = ScientistWorkflow(Settings(dashscope_api_key=""))
    run = ResearchRun(
        domain="energy_materials",
        question="q",
        constraints=ResearchConstraints(),
    )
    calls = 0

    async def flaky(_run: ResearchRun) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("temporary")

    await workflow._step(run, "literature_search", flaky)

    assert calls == 2
    assert run.steps[-1].status == "completed"
    assert run.steps[-1].attempts == 2
    assert [event.event for event in run.steps[-1].events] == [
        "started",
        "retrying",
        "completed",
    ]


@pytest.mark.asyncio
async def test_second_retryable_failure_waits_for_action() -> None:
    workflow = ScientistWorkflow(Settings(dashscope_api_key=""))
    run = ResearchRun(
        domain="energy_materials",
        question="q",
        constraints=ResearchConstraints(),
    )

    async def always_fails(_run: ResearchRun) -> None:
        raise httpx.ReadTimeout("temporary")

    with pytest.raises(StepNeedsAction):
        await workflow._step(run, "literature_search", always_fails)

    assert run.status == "paused"
    assert run.current_stage == "literature_search"
    assert run.steps[-1].status == "waiting_action"
    assert run.steps[-1].attempts == 2
    assert run.steps[-1].retryable is True


@pytest.mark.asyncio
async def test_non_retryable_failure_waits_without_second_attempt() -> None:
    workflow = ScientistWorkflow(Settings(dashscope_api_key=""))
    run = ResearchRun(
        domain="energy_materials",
        question="q",
        constraints=ResearchConstraints(),
    )
    calls = 0

    async def invalid(_run: ResearchRun) -> None:
        nonlocal calls
        calls += 1
        raise ValueError("invalid input")

    with pytest.raises(StepNeedsAction):
        await workflow._step(run, "baseline_intake", invalid)

    assert calls == 1
    assert run.steps[-1].attempts == 1
    assert run.steps[-1].retryable is False
