import pytest
from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


@pytest.mark.asyncio
async def test_re_search_replaces_dataset_papers_and_sets_evidence_changed(monkeypatch, tmp_path):
    wf = ScientistWorkflow(Settings(dashscope_api_key="", max_papers=3))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints())
    from app.schemas.paper import Paper
    run.papers = [
        Paper(paper_id="p1", title="STEAD dataset", baseline_eligible=False, paper_role="dataset_benchmark"),
        Paper(paper_id="p2", title="Seismic CNN model", baseline_eligible=True, paper_role="method_model"),
    ]
    async def fake_search(queries, *, max_papers, enable_semantic_scholar=False, enable_arxiv=True, domain=""):
        return [Paper(paper_id="new1", title="EQTransformer reproduction github", baseline_eligible=True)]
    monkeypatch.setattr(wf.literature_router, "search", fake_search)
    await wf._re_search_literature(run)
    assert run.re_search_round == 1
    assert run.evidence_changed is True  # dataset paper replaced
    assert all(p.paper_id != "p1" for p in run.papers)  # dataset paper gone


@pytest.mark.asyncio
async def test_re_search_noop_non_seismic(monkeypatch, tmp_path):
    wf = ScientistWorkflow(Settings(dashscope_api_key=""))
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    await wf._re_search_literature(run)
    assert run.re_search_round == 0
    assert run.evidence_changed is False
