import pytest

from app.config import Settings
from app.schemas.citation import CitationVerificationReport, CitationVerificationResult
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


@pytest.mark.asyncio
async def test_workflow_completes_with_mocked_literature(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)

    async def fake_search(queries, *, max_papers: int, enable_semantic_scholar: bool = False, enable_arxiv: bool = True):
        assert enable_arxiv is True
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

    async def fake_verify_many(papers, *, enable_semantic_scholar: bool = False):
        for paper in papers:
            paper.verification_status = "verified"
            paper.verified_by.append("crossref")
            paper.title_match_score = 0.95
            paper.verification_method = "crossref_doi"
            paper.verification_confidence = 0.95
            paper.report_eligible = True
        return papers, CitationVerificationReport(
            total=len(papers),
            verified=len(papers),
            integrity_score=1,
            results=[
                CitationVerificationResult(
                    paper_id=paper.paper_id,
                    title=paper.title,
                    status="verified",
                    confidence=0.95,
                    method="crossref_doi",
                    doi=paper.doi,
                )
                for paper in papers
            ],
        )

    monkeypatch.setattr(workflow.literature_router, "search", fake_search)
    monkeypatch.setattr(workflow.citation_verifier, "verify_many", fake_verify_many)

    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1),
    )

    result = await workflow.run(run)

    assert result.status == "completed"
    assert result.report is not None
    assert result.claim_audit is not None
    assert result.perspectives
    assert result.knowledge_cards
    assert result.workspace_path
    assert "research_log" in result.workspace_artifacts
    assert result.hypotheses[0].selected is True
    assert result.evidence[0].verified is True


@pytest.mark.asyncio
async def test_workflow_can_disable_arxiv(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)

    async def fake_search(queries, *, max_papers: int, enable_semantic_scholar: bool = False, enable_arxiv: bool = True):
        assert enable_arxiv is False
        return [
            Paper(
                paper_id="openalex_001",
                title="OpenAlex-only candidate",
                doi="10.1000/openalex",
                verification_status="candidate",
                verified_by=["openalex"],
                source_api="openalex",
            )
        ]

    async def fake_verify_many(papers, *, enable_semantic_scholar: bool = False):
        for paper in papers:
            paper.verification_status = "verified"
            paper.verification_method = "openalex_title"
            paper.verification_confidence = 0.95
            paper.report_eligible = True
        return papers, CitationVerificationReport(total=len(papers), verified=len(papers), integrity_score=1)

    monkeypatch.setattr(workflow.literature_router, "search", fake_search)
    monkeypatch.setattr(workflow.citation_verifier, "verify_many", fake_verify_many)

    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=1, enable_arxiv=False),
    )

    result = await workflow.run(run)

    assert result.status == "completed"
    assert result.constraints.enable_arxiv is False
    assert {paper.source_api for paper in result.papers} == {"openalex"}


@pytest.mark.asyncio
async def test_workflow_uses_semantic_scholar_when_enabled(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)

    async def fake_router_search(queries, *, max_papers: int, enable_semantic_scholar: bool = False, enable_arxiv: bool = True):
        assert enable_semantic_scholar is True
        assert enable_arxiv is True
        return [
            Paper(
                paper_id="openalex_001",
                title="OpenAlex candidate",
                doi="10.1000/openalex",
                verification_status="candidate",
                verified_by=["openalex"],
                source_api="openalex",
            ),
            Paper(
                paper_id="S2:semantic_001",
                title="Semantic Scholar candidate",
                doi="10.1000/semantic",
                verification_status="candidate",
                verified_by=["semantic_scholar"],
                source_api="semantic_scholar",
            ),
            Paper(
                paper_id="arxiv:2401.00001",
                title="arXiv candidate",
                arxiv_id="2401.00001",
                verification_status="candidate",
                verified_by=["arxiv"],
                source_api="arxiv",
            ),
        ][:max_papers]

    async def fake_verify_many(papers, *, enable_semantic_scholar: bool = False):
        for paper in papers:
            paper.verification_status = "verified"
            paper.verification_method = "openalex_title"
            paper.verification_confidence = 0.95
            paper.report_eligible = True
        return papers, CitationVerificationReport(total=len(papers), verified=len(papers), integrity_score=1)

    monkeypatch.setattr(workflow.literature_router, "search", fake_router_search)
    monkeypatch.setattr(workflow.citation_verifier, "verify_many", fake_verify_many)

    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=2, enable_semantic_scholar=True),
    )

    result = await workflow.run(run)

    assert result.status == "completed"
    assert {paper.source_api for paper in result.papers} == {"openalex", "semantic_scholar"}
    assert len(result.papers) == 2
