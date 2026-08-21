from fastapi.testclient import TestClient

from app.main import app
from app.schemas.common import AgentStep, RunStatus
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.in_memory import run_store


client = TestClient(app)


def _waiting_run(step_name: str = "literature_mining", *, skippable: bool = True) -> ResearchRun:
    run = ResearchRun(
        domain="energy_materials",
        question="q",
        constraints=ResearchConstraints(),
    )
    run.status = RunStatus.paused
    run.current_stage = step_name
    run.steps = [
        AgentStep(
            name=step_name,
            status="waiting_action",
            attempts=2,
            retryable=True,
            skippable=skippable,
        )
    ]
    return run_store.create(run)


def test_skip_rejects_critical_step() -> None:
    run = _waiting_run("report_writer", skippable=False)

    response = client.post(
        f"/api/runs/{run.run_id}/steps/report_writer/action",
        json={"action": "skip"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "critical step cannot be skipped"


def test_recover_converts_orphaned_running_step_to_waiting_action() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="q",
        constraints=ResearchConstraints(),
        status=RunStatus.running,
        current_stage="literature_search",
        steps=[
            AgentStep(
                name="planner",
                status="completed",
                summary="done",
            ),
            AgentStep(
                name="literature_search",
                status="running",
                summary="searching",
                attempts=1,
            ),
        ],
    )
    run_store.create(run)

    response = client.post(f"/api/runs/{run.run_id}/recover")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "paused"
    assert payload["resume_count"] == 1
    assert payload["last_action"]["action"] == "recover"
    assert payload["steps"][0]["status"] == "completed"
    assert payload["steps"][1]["status"] == "waiting_action"


def test_recover_rejects_completed_run() -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="q",
        constraints=ResearchConstraints(),
        status=RunStatus.completed,
        current_stage="completed",
    )
    run_store.create(run)

    response = client.post(f"/api/runs/{run.run_id}/recover")

    assert response.status_code == 409
