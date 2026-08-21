import pytest

from app.schemas.common import AgentStep, RunStatus
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.in_memory import run_store
from app.workflows.scientist_workflow import ScientistWorkflow


def _workflow_without_dependencies() -> ScientistWorkflow:
    workflow = object.__new__(ScientistWorkflow)
    workflow._write_workspace = lambda _run: None
    return workflow


def _run() -> ResearchRun:
    return ResearchRun(
        display_name="地震事件分类可信研究",
        domain="seismic_event_classification",
        question="基于真实数据开展地震事件分类研究",
        constraints=ResearchConstraints(max_papers=3),
        status=RunStatus.running,
    )


@pytest.mark.asyncio
async def test_pause_request_stops_at_the_completed_step_boundary() -> None:
    workflow = _workflow_without_dependencies()
    run = _run()
    run_store.create(run)

    async def current_step(current: ResearchRun) -> None:
        current.control_action = "pause"

    try:
        with pytest.raises(Exception) as caught:
            await workflow._step(run, "planner", current_step)

        assert caught.type.__name__ == "RunControlSignal"
        assert run.status == RunStatus.paused
        assert run.pause_reason == "user"
        assert run.control_action == "none"
        assert run.steps[-1].status == "completed"
        assert run.current_stage == "planner"
    finally:
        run_store.delete(run.run_id)


@pytest.mark.asyncio
async def test_abandon_request_prevents_the_next_step_from_starting() -> None:
    workflow = _workflow_without_dependencies()
    run = _run()
    run.control_action = "abandon"
    run.status = RunStatus.abandoned
    executed = False

    async def next_step(_current: ResearchRun) -> None:
        nonlocal executed
        executed = True

    with pytest.raises(Exception) as caught:
        await workflow._step(run, "literature_search", next_step)

    assert caught.type.__name__ == "RunControlSignal"
    assert executed is False
    assert run.status == RunStatus.abandoned
    assert run.steps == []


@pytest.mark.asyncio
async def test_user_resume_keeps_existing_steps_and_uses_incomplete_pipeline() -> None:
    workflow = _workflow_without_dependencies()
    run = _run()
    run.status = RunStatus.paused
    run.pause_reason = "user"
    run.steps = [AgentStep(name="planner", status="completed", summary="已有规划")]
    seen_steps: list[str] = []

    async def resume_incomplete(current: ResearchRun) -> None:
        seen_steps.extend(step.name for step in current.steps)
        current.status = RunStatus.completed

    workflow._resume_incomplete_pipeline = resume_incomplete

    result = await workflow.resume_user_run(run)

    assert result.status == RunStatus.completed
    assert seen_steps == ["planner"]
    assert [step.name for step in result.steps] == ["planner"]
