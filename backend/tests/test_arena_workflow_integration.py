import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content

    async def complete(self, request):
        from app.llm.interface import LLMResponse
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


@pytest.mark.asyncio
async def test_seismic_run_uses_arena_and_auto_baseline(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)

    # Stub the arena agent to avoid real LLM/parallel cost.
    async def fake_arena_arun(self, mode, gaps, evidence, data_profiles, idea_brief, papers, *, run_id, avoid_prior_art=None):
        from app.schemas.arena import HypothesisArenaResult
        from app.schemas.hypothesis import Hypothesis
        h = Hypothesis(hypothesis_id="H1", statement="s", rationale="r", novelty_claim="n", verification_path="v", selected=True)
        result = HypothesisArenaResult(arena_id="a1", mode=mode, candidates=[], ranking=["H1"], selected_for_experiment="H1", switchback_candidate=None)
        return result, [h]
    monkeypatch.setattr(workflow.arena_agent.__class__, "arun", fake_arena_arun)

    # Stub baseline discovery + verify (no real GitHub).
    async def fake_extract(papers, *, max_pdf=5, transport=None):
        return papers
    monkeypatch.setattr("app.workflows.scientist_workflow.extract_code_urls_async", fake_extract)

    async def fake_discover(self, papers, task, *, run_id):
        from app.schemas.baseline import BaselineCandidate
        return [BaselineCandidate(baseline_id="b1", paper_id="p1", paper_title="t", code_url="https://github.com/a/b", code_source="paper_abstract", task_match="seismic", input_type="waveform", verified_repo=True)]
    monkeypatch.setattr(workflow.baseline_discovery.__class__, "arun", fake_discover)

    async def fake_verify(self, candidate, *, run_id):
        return candidate
    monkeypatch.setattr(workflow.repo_verifier.__class__, "arun", fake_verify)

    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(max_papers=1), mode="discovery")

    await workflow._run_arena(run)
    assert run.arena_result is not None
    assert run.arena_result.selected_for_experiment == "H1"
    assert run.hypotheses[0].selected is True

    await workflow._extract_code_urls(run)
    await workflow._discover_baselines_auto(run)
    await workflow._verify_baselines_auto(run)
    assert run.baseline_candidates
    assert run.baseline_candidates[0].code_url == "https://github.com/a/b"


@pytest.mark.asyncio
async def test_non_seismic_run_skips_arena(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints(max_papers=1), mode="discovery")
    # _run_after_evidence_review for non-seismic should call the existing _generate_and_critique, not arena.
    # Just assert the arena method is a no-op / not invoked by checking arena_result stays None after a non-seismic arena call.
    await workflow._run_arena(run)
    # non-seismic arena is a no-op
    assert run.arena_result is None


@pytest.mark.asyncio
async def test_seismic_classifies_papers_and_verifies_by_priority(monkeypatch) -> None:
    from app.config import Settings
    from app.schemas.paper import Paper
    from app.schemas.run import ResearchConstraints, ResearchRun
    from app.workflows.scientist_workflow import ScientistWorkflow
    wf = ScientistWorkflow(Settings(dashscope_api_key="", max_papers=2))

    async def fake_classify(self, papers, *, run_id):
        for p in papers: p.paper_role, p.baseline_eligible = "method_model", True
        return papers
    monkeypatch.setattr(wf.paper_classifier.__class__, "arun", fake_classify)

    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(max_papers=1), mode="discovery")
    run.papers = [Paper(paper_id="p1", title="Seismic CNN")]
    await wf._classify_papers(run)
    assert run.papers[0].paper_role == "method_model"
    assert run.papers[0].baseline_eligible is True
