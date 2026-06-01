import httpx
import pytest

from app.config import Settings
from app.tools.semantic_scholar_client import SemanticScholarClient


@pytest.mark.asyncio
async def test_semantic_scholar_search_maps_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        assert request.url.path == "/graph/v1/paper/search"
        assert params["query"] == "solid electrolyte"
        assert params["limit"] == "2"
        assert "externalIds" in params["fields"]
        assert request.headers["x-api-key"] == "s2-key"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "paperId": "abc123",
                        "externalIds": {"DOI": "https://doi.org/10.3000/s2"},
                        "url": "https://www.semanticscholar.org/paper/abc123",
                        "title": "Semantic <sub>Scholar</sub> electrolyte paper",
                        "authors": [{"name": "Ada Lovelace"}, {"name": "Tu Youyou"}],
                        "year": 2023,
                        "publicationDate": "2023-03-02",
                        "venue": "S2 &amp; Materials",
                        "abstract": "A structured abstract.",
                        "citationCount": 9,
                        "openAccessPdf": {"url": "https://example.org/paper.pdf"},
                        "isOpenAccess": True,
                        "fieldsOfStudy": ["Materials Science", "Chemistry"],
                        "publicationTypes": ["JournalArticle"],
                    }
                ]
            },
        )

    client = SemanticScholarClient(
        Settings(semantic_scholar_api_key="s2-key"),
        transport=httpx.MockTransport(handler),
    )

    papers = await client.search("solid electrolyte", 2)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.paper_id == "S2:abc123"
    assert paper.semantic_scholar_id == "abc123"
    assert paper.doi == "10.3000/s2"
    assert paper.title == "Semantic Scholar electrolyte paper"
    assert paper.authors == ["Ada Lovelace", "Tu Youyou"]
    assert paper.year == 2023
    assert paper.publication_date == "2023-03-02"
    assert paper.source_url == "https://www.semanticscholar.org/paper/abc123"
    assert paper.pdf_url == "https://example.org/paper.pdf"
    assert paper.venue == "S2 & Materials"
    assert paper.cited_by_count == 9
    assert paper.fields_of_study == ["Materials Science", "Chemistry"]
    assert paper.source_api == "semantic_scholar"
    assert paper.verified_by == ["semantic_scholar"]
    assert paper.verification_status == "candidate"


@pytest.mark.asyncio
async def test_semantic_scholar_search_handles_empty_query_and_empty_titles() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "x-api-key" not in request.headers
        return httpx.Response(
            200,
            json={
                "data": [
                    {"paperId": "empty", "title": ""},
                    {"paperId": "ok", "title": "Usable paper", "externalIds": {"DOI": "doi:10.4000/ok"}},
                ]
            },
        )

    client = SemanticScholarClient(Settings(), transport=httpx.MockTransport(handler))

    assert await client.search(" ", 5) == []
    assert await client.search("usable", 0) == []
    papers = await client.search("usable", 5)

    assert len(papers) == 1
    assert papers[0].paper_id == "S2:ok"
    assert papers[0].doi == "10.4000/ok"


@pytest.mark.asyncio
async def test_semantic_scholar_search_returns_empty_on_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    client = SemanticScholarClient(Settings(), transport=httpx.MockTransport(handler))

    assert await client.search("rate limited", 3) == []
