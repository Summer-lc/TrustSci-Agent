from fastapi.testclient import TestClient

from app.api import routes_runs
from app.main import app
from app.schemas.common import RunStatus
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.in_memory import run_store


client = TestClient(app)


def _stored_run(*, status: RunStatus, pause_reason: str | None = None) -> ResearchRun:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="基于真实波形数据的地震事件分类研究",
        constraints=ResearchConstraints(max_papers=3),
        status=status,
    )
    run.pause_reason = pause_reason
    return run_store.create(run)


def test_create_run_generates_a_concrete_display_name() -> None:
    response = client.post(
        "/api/runs",
        json={
            "domain": "seismic_event_classification",
            "question": "  基于真实数据的   地震事件分类可信模型研究  ",
            "constraints": {"max_papers": 3},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "基于真实数据的 地震事件分类可信模型研究"
    assert not body["display_name"].startswith("run_")
    run_store.delete(body["run_id"])


def test_pause_requests_a_safe_stop_for_a_running_run() -> None:
    run = _stored_run(status=RunStatus.running)
    try:
        response = client.post(f"/api/runs/{run.run_id}/pause")

        assert response.status_code == 200
        assert response.json()["status"] == "running"
        assert response.json()["control_action"] == "pause"
        assert response.json()["last_action"]["action"] == "pause_requested"
    finally:
        run_store.delete(run.run_id)


def test_user_paused_run_can_resume_without_clearing_previous_steps(monkeypatch) -> None:
    resumed: list[str] = []

    class FakeWorkflow:
        async def resume_user_run(self, run: ResearchRun) -> ResearchRun:
            resumed.append(run.run_id)
            return run

    monkeypatch.setattr(routes_runs, "build_workflow", lambda _settings: FakeWorkflow())
    run = _stored_run(status=RunStatus.paused, pause_reason="user")
    try:
        response = client.post(f"/api/runs/{run.run_id}/resume")

        assert response.status_code == 200
        assert response.json()["status"] == "running"
        assert response.json()["pause_reason"] is None
        assert response.json()["control_action"] == "none"
        assert resumed == [run.run_id]
    finally:
        run_store.delete(run.run_id)


def test_abandoned_run_is_terminal_and_cannot_restart(monkeypatch) -> None:
    class FakeWorkflow:
        async def run(self, run: ResearchRun) -> ResearchRun:
            return run

        async def continue_run(self, run: ResearchRun) -> ResearchRun:
            return run

    monkeypatch.setattr(routes_runs, "build_workflow", lambda _settings: FakeWorkflow())
    run = _stored_run(status=RunStatus.running)
    try:
        abandoned = client.post(f"/api/runs/{run.run_id}/abandon")
        resumed = client.post(f"/api/runs/{run.run_id}/resume")
        restarted = client.post(f"/api/runs/{run.run_id}/start")
        continued = client.post(f"/api/runs/{run.run_id}/continue")
        recovered = client.post(f"/api/runs/{run.run_id}/recover")

        assert abandoned.status_code == 200
        assert abandoned.json()["status"] == "abandoned"
        assert abandoned.json()["control_action"] == "abandon"
        assert resumed.status_code == 409
        assert restarted.status_code == 409
        assert continued.status_code == 409
        assert recovered.status_code == 409
    finally:
        run_store.delete(run.run_id)
