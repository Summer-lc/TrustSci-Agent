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

