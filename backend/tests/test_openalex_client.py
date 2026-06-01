import httpx
import pytest

from app.config import Settings
from app.tools.openalex_client import OpenAlexClient


@pytest.mark.asyncio
async def test_openalex_search_maps_real_work_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        assert request.url.path == "/works"
        assert params["search"] == "solid electrolyte"
        assert params["per-page"] == "2"
        assert params["mailto"] == "researcher@example.com"
        assert "display_name" in params["select"]
        assert params["filter"] == "is_retracted:false,is_paratext:false"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "doi": "https://doi.org/10.1000/example",
                        "display_name": "Solid <sub>electrolytes</sub> for lithium batteries",
                        "publication_year": 2024,
                        "publication_date": "2024-02-01",
                        "type": "article",
                        "cited_by_count": 42,
                        "is_retracted": False,
                        "is_paratext": False,
                        "authorships": [
                            {"author": {"display_name": "Ada Lovelace"}},
                            {"author": {"display_name": "Tu Youyou"}},
                        ],
                        "primary_location": {
                            "landing_page_url": "https://publisher.example/paper",
                            "pdf_url": None,
                            "source": {"display_name": "Journal of Test Materials"},
                        },
                        "best_oa_location": {
                            "landing_page_url": "https://repository.example/paper",
                            "pdf_url": "https://repository.example/paper.pdf",
                            "source": {"display_name": "Repository"},
                        },
                        "open_access": {"is_oa": True, "oa_url": "https://repository.example/paper"},
                        "abstract_inverted_index": {
                            "Solid": [0],
                            "electrolytes": [1],
                            "conduct": [2],
                            "ions": [3],
                        },
                    }
                ]
            },
        )

    client = OpenAlexClient(
        Settings(openalex_email="researcher@example.com"),
        transport=httpx.MockTransport(handler),
    )

    papers = await client.search("solid electrolyte", 2)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.paper_id == "W123"
    assert paper.openalex_id == "https://openalex.org/W123"
    assert paper.doi == "10.1000/example"
    assert paper.title == "Solid electrolytes for lithium batteries"
    assert paper.authors == ["Ada Lovelace", "Tu Youyou"]
    assert paper.year == 2024
    assert paper.publication_date == "2024-02-01"
    assert paper.source_url == "https://publisher.example/paper"
    assert paper.pdf_url == "https://repository.example/paper.pdf"
    assert paper.venue == "Journal of Test Materials"
    assert paper.abstract == "Solid electrolytes conduct ions"
    assert paper.work_type == "article"
    assert paper.cited_by_count == 42
    assert paper.is_open_access is True
    assert paper.source_api == "openalex"
    assert paper.verified_by == ["openalex"]
    assert paper.verification_status == "candidate"


@pytest.mark.asyncio
async def test_openalex_search_filters_bad_results_and_handles_empty_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W_RETRACTED",
                        "display_name": "Retracted work",
                        "is_retracted": True,
                        "is_paratext": False,
                    },
                    {
                        "id": "https://openalex.org/W_PARATEXT",
                        "display_name": "Editorial content",
                        "is_retracted": False,
                        "is_paratext": True,
                    },
                    {
                        "id": "https://openalex.org/W_EMPTY",
                        "display_name": "",
                        "is_retracted": False,
                        "is_paratext": False,
                    },
                    {
                        "id": "https://openalex.org/W_OK",
                        "display_name": "A usable scholarly work",
                        "doi": "doi:10.2000/usable",
                        "is_retracted": False,
                        "is_paratext": False,
                    },
                ]
            },
        )

    client = OpenAlexClient(Settings(), transport=httpx.MockTransport(handler))

    assert await client.search("   ", 5) == []
    assert await client.search("usable work", 0) == []
    papers = await client.search("usable work", 5)

    assert len(papers) == 1
    assert papers[0].paper_id == "W_OK"
    assert papers[0].doi == "10.2000/usable"
