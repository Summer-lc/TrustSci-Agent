import json

from app.schemas.common import RunStatus
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.workspace import RunWorkspace


def _snapshot_run() -> ResearchRun:
    return ResearchRun(
        domain="seismic_event_classification",
        question="基于真实波形数据的地震事件分类可信研究",
        constraints=ResearchConstraints(max_papers=3),
    )


def test_legacy_workspace_gets_a_concrete_name_when_loaded(tmp_path) -> None:
    workspace = RunWorkspace(tmp_path)
    run = _snapshot_run()
    workspace.write_snapshot(run)
    snapshot_path = workspace.run_dir(run.run_id) / "run.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload.pop("display_name", None)
    snapshot_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    restored = workspace.load_snapshot(run.run_id)

    assert restored.display_name == "基于真实波形数据的地震事件分类可信研究"


def test_interrupted_pause_request_restores_as_user_paused(tmp_path) -> None:
    workspace = RunWorkspace(tmp_path)
    run = _snapshot_run()
    run.status = RunStatus.running
    run.current_stage = "literature_search"
    run.control_action = "pause"
    workspace.write_snapshot(run)

    restored = workspace.load_snapshot(run.run_id)

    assert restored.status == RunStatus.paused
    assert restored.pause_reason == "user"
    assert restored.control_action == "none"
    assert restored.current_stage == "literature_search"
