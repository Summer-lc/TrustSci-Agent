from app.main import app
from app.schemas.baseline import BaselineCandidate
from app.schemas.feedback_loop import NoveltyVerdict
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.in_memory import run_store
from fastapi.testclient import TestClient

client = TestClient(app)


def _seed_run() -> ResearchRun:
    run = ResearchRun(domain="seismic_event_classification", question="fuse waveform with spectrogram", constraints=ResearchConstraints(), mode="idea_refinement")
    run.papers = [Paper(paper_id="p1", title="Seismic event classification with CNN", arxiv_id="2401.00001")]
    return run_store.create(run)


async def _discover_stub(run):
    from app.schemas.baseline import BaselineCandidate
    run.baseline_candidates = [BaselineCandidate(baseline_id="b1", paper_id="p1", paper_title="Seismic CNN", code_url="https://github.com/a/b", code_source="github_search", task_match="seismic", input_type="waveform")]
    run.novelty_verdict = NoveltyVerdict()
    return run


def test_discover_endpoint_populates_candidates(monkeypatch) -> None:
    run = _seed_run()
    from app.api import routes_runs
    # The route calls the module-level helper; patch it so no real GitHub/PwC HTTP fires.
    monkeypatch.setattr(routes_runs, "_discover_baselines_for_run", _discover_stub)

    resp = client.post(f"/api/runs/{run.run_id}/baselines/discover")
    assert resp.status_code == 200
    body = resp.json()
    assert body["baseline_candidates"]
    assert body["baseline_candidates"][0]["code_url"] == "https://github.com/a/b"
    assert body["novelty_verdict"] is not None
    run_store.delete(run.run_id)


def test_verify_repo_endpoint_updates_candidate(monkeypatch) -> None:
    run = _seed_run()
    run.baseline_candidates = [BaselineCandidate(baseline_id="b1", paper_id="p1", paper_title="Seismic CNN", code_url="https://github.com/a/b", code_source="github_search", task_match="seismic", input_type="waveform")]
    run_store.save(run)

    async def fake_verify(candidate, *, run_id):
        candidate.verified_repo = True
        candidate.reproduction_status = "verified"
        candidate.reproducibility_score = 0.8
        return candidate

    from app.api import routes_runs
    monkeypatch.setattr(routes_runs, "_verify_repo_for_candidate", fake_verify)

    resp = client.post(f"/api/runs/{run.run_id}/baselines/b1/verify-repo")
    assert resp.status_code == 200
    cand = next(c for c in resp.json()["baseline_candidates"] if c["baseline_id"] == "b1")
    assert cand["verified_repo"] is True
    assert cand["reproducibility_score"] == 0.8
    run_store.delete(run.run_id)
