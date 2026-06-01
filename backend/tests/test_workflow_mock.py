import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


@pytest.mark.asyncio
async def test_workflow_completes_with_mocked_literature(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)

    async def fake_search(query: str, limit: int):
        from app.schemas.paper import Paper

        return [
            Paper(
                paper_id="paper_001",
                title="Solid-state electrolytes for lithium batteries",
                doi="10.1038/example",
                abstract="Solid-state electrolyte studies connect structure and ionic transport.",
                verification_status="candidate",
                verified_by=["openalex"],
            )
        ]

    async def fake_verify(paper):
        paper.verification_status = "verified"
        paper.verified_by.append("crossref")
        paper.title_match_score = 0.95
        return paper

    monkeypatch.setattr(workflow.openalex, "search", fake_search)
    monkeypatch.setattr(workflow.crossref, "verify", fake_verify)

    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1),
    )

    result = await workflow.run(run)

    assert result.status == "completed"
    assert result.report is not None
    assert result.hypotheses[0].selected is True
    assert result.evidence[0].verified is True


@pytest.mark.asyncio
async def test_workflow_uses_semantic_scholar_when_enabled(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)

    async def fake_openalex_search(query: str, limit: int):
        from app.schemas.paper import Paper

        return [
            Paper(
                paper_id="openalex_001",
                title="OpenAlex candidate",
                doi="10.1000/openalex",
                verification_status="candidate",
                verified_by=["openalex"],
                source_api="openalex",
            )
        ][:limit]

    async def fake_semantic_search(query: str, limit: int):
        from app.schemas.paper import Paper

        return [
            Paper(
                paper_id="S2:semantic_001",
                title="Semantic Scholar candidate",
                doi="10.1000/semantic",
                verification_status="candidate",
                verified_by=["semantic_scholar"],
                source_api="semantic_scholar",
            )
        ][:limit]

    async def fake_verify(paper):
        paper.verification_status = "verified"
        if "crossref" not in paper.verified_by:
            paper.verified_by.append("crossref")
        paper.title_match_score = 0.95
        return paper

    monkeypatch.setattr(workflow.openalex, "search", fake_openalex_search)
    monkeypatch.setattr(workflow.semantic_scholar, "search", fake_semantic_search)
    monkeypatch.setattr(workflow.crossref, "verify", fake_verify)

    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=2, enable_semantic_scholar=True),
    )

    result = await workflow.run(run)

    assert result.status == "completed"
    assert {paper.source_api for paper in result.papers} == {"openalex", "semantic_scholar"}
    assert len(result.papers) == 2
