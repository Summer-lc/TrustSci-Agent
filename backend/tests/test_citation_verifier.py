import httpx
import pytest

from app.config import Settings
from app.schemas.paper import Paper
from app.tools.citation_verifier import CitationVerifier


class FakeCrossref:
    async def verify(self, paper: Paper) -> Paper:
        paper.verification_status = "suspicious"
        paper.title_match_score = 0.2
        return paper


class FakeArxiv:
    def __init__(self, by_id: Paper | None = None, search_results: list[Paper] | None = None) -> None:
        self.by_id = by_id
        self.search_results = search_results or []

    async def get_by_id(self, arxiv_id: str) -> Paper | None:
        return self.by_id

    async def search(self, query: str, limit: int) -> list[Paper]:
        return self.search_results[:limit]


class FakeSearchClient:
    def __init__(self, results: list[Paper]) -> None:
        self.results = results

    async def search(self, query: str, limit: int) -> list[Paper]:
        return self.results[:limit]


@pytest.mark.asyncio
async def test_citation_verifier_uses_arxiv_id_layer() -> None:
    paper = Paper(
        paper_id="candidate",
        title="Solid Electrolyte Discovery with Machine Learning",
        arxiv_id="2401.01234",
        source_api="arxiv",
    )
    verifier = CitationVerifier(
        Settings(),
        crossref=FakeCrossref(),  # type: ignore[arg-type]
        arxiv=FakeArxiv(
            by_id=Paper(
                paper_id="arxiv:2401.01234",
                title="Solid Electrolyte Discovery with Machine Learning",
                arxiv_id="2401.01234",
                source_url="https://arxiv.org/abs/2401.01234",
                source_api="arxiv",
            )
        ),  # type: ignore[arg-type]
        openalex=FakeSearchClient([]),  # type: ignore[arg-type]
        semantic_scholar=FakeSearchClient([]),  # type: ignore[arg-type]
    )

    papers, report = await verifier.verify_many([paper])

    assert report.total == 1
    assert report.verified == 1
    assert report.integrity_score == 1
    assert papers[0].verification_status == "verified"
    assert papers[0].verification_method == "arxiv_id"
    assert papers[0].report_eligible is True


@pytest.mark.asyncio
async def test_citation_verifier_uses_datacite_doi_fallback() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/dois/10.48550/arXiv.2401.01234"
        return httpx.Response(
            200,
            json={
                "data": {
                    "attributes": {
                        "titles": [{"title": "Solid Electrolyte Discovery with Machine Learning"}]
                    }
                }
            },
        )

    paper = Paper(
        paper_id="candidate",
        title="Solid Electrolyte Discovery with Machine Learning",
        doi="10.48550/arXiv.2401.01234",
    )
    verifier = CitationVerifier(
        Settings(),
        crossref=FakeCrossref(),  # type: ignore[arg-type]
        arxiv=FakeArxiv(),  # type: ignore[arg-type]
        openalex=FakeSearchClient([]),  # type: ignore[arg-type]
        semantic_scholar=FakeSearchClient([]),  # type: ignore[arg-type]
        datacite_transport=httpx.MockTransport(handler),
    )

    papers, report = await verifier.verify_many([paper])

    assert report.verified == 1
    assert papers[0].verification_method == "datacite_doi"
    assert "datacite" in papers[0].verified_by


@pytest.mark.asyncio
async def test_citation_verifier_marks_partial_title_match_suspicious() -> None:
    paper = Paper(paper_id="candidate", title="Solid Electrolyte Discovery with Machine Learning")
    verifier = CitationVerifier(
        Settings(),
        crossref=FakeCrossref(),  # type: ignore[arg-type]
        arxiv=FakeArxiv(),  # type: ignore[arg-type]
        openalex=FakeSearchClient(
            [
                Paper(
                    paper_id="W1",
                    title="Solid Electrolyte Discovery",
                    source_url="https://openalex.org/W1",
                    source_api="openalex",
                )
            ]
        ),  # type: ignore[arg-type]
        semantic_scholar=FakeSearchClient([]),  # type: ignore[arg-type]
    )

    papers, report = await verifier.verify_many([paper])

    assert report.suspicious == 1
    assert papers[0].verification_status == "suspicious"
    assert papers[0].report_eligible is False
