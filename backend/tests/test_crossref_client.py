import httpx
import pytest

from app.config import Settings
from app.schemas.paper import Paper
from app.tools.crossref_client import CrossrefClient


@pytest.mark.asyncio
async def test_crossref_verifies_matching_doi_title_and_year() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/works/10.1000/example"
        assert request.url.params["mailto"] == "crossref@example.com"
        assert "TrustSci-Agent/0.1" in request.headers["user-agent"]
        assert "mailto:crossref@example.com" in request.headers["user-agent"]
        return httpx.Response(
            200,
            json={
                "message": {
                    "DOI": "10.1000/example",
                    "title": ["Solid electrolytes for lithium batteries"],
                    "container-title": ["Journal of Test &amp; Materials"],
                    "type": "journal-article",
                    "is-referenced-by-count": 17,
                    "published-print": {"date-parts": [[2024, 5, 2]]},
                    "author": [
                        {"given": "Ada", "family": "Lovelace"},
                        {"name": "Tu Youyou"},
                    ],
                }
            },
        )

    paper = Paper(
        paper_id="W123",
        title="Solid electrolyte materials for lithium batteries",
        year=2024,
        doi="10.1000/example",
        verified_by=["openalex"],
        source_api="openalex",
    )
    client = CrossrefClient(
        Settings(crossref_email="crossref@example.com", openalex_email="openalex@example.com"),
        transport=httpx.MockTransport(handler),
    )

    verified = await client.verify(paper)

    assert verified.verification_status == "verified"
    assert verified.title_match_score is not None
    assert verified.title_match_score >= 0.82
    assert verified.verified_by == ["openalex", "crossref"]
    assert verified.doi == "10.1000/example"
    assert verified.venue == "Journal of Test & Materials"
    assert verified.work_type == "journal-article"
    assert verified.cited_by_count == 17
    assert verified.publication_date == "2024-05-02"


@pytest.mark.asyncio
async def test_crossref_marks_mismatch_and_failures_suspicious() -> None:
    def mismatch_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "DOI": "https://doi.org/10.1000/mismatch",
                    "title": ["Unrelated biomedical paper"],
                    "issued": {"date-parts": [[2015]]},
                }
            },
        )

    mismatch = Paper(
        paper_id="W_BAD",
        title="Solid electrolyte materials for lithium batteries",
        year=2024,
        doi="10.1000/mismatch",
    )
    client = CrossrefClient(Settings(), transport=httpx.MockTransport(mismatch_handler))
    result = await client.verify(mismatch)

    assert result.verification_status == "suspicious"
    assert "crossref" in result.verified_by
    assert result.doi == "10.1000/mismatch"

    missing_doi = await client.verify(Paper(paper_id="no_doi", title="No DOI"))
    assert missing_doi.verification_status == "suspicious"

    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    failed = await CrossrefClient(Settings(), transport=httpx.MockTransport(error_handler)).verify(
        Paper(paper_id="W_FAIL", title="A paper", doi="10.1000/fail")
    )
    assert failed.verification_status == "suspicious"
