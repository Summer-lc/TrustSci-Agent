import pytest

from app.config import Settings
from app.schemas.paper import Paper
from app.tools.literature_router import LiteratureRouter


class FakeClient:
    def __init__(self, source: str, papers: list[Paper]) -> None:
        self.source = source
        self.papers = papers
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, limit: int) -> list[Paper]:
        self.calls.append((query, limit))
        return self.papers[:limit]


@pytest.mark.asyncio
async def test_literature_router_merges_sources_and_deduplicates() -> None:
    openalex = FakeClient(
        "openalex",
        [
            Paper(
                paper_id="W1",
                title="Solid Electrolyte Discovery",
                doi="10.1000/example",
                cited_by_count=8,
                source_api="openalex",
                verified_by=["openalex"],
            )
        ],
    )
    semantic = FakeClient(
        "semantic_scholar",
        [
            Paper(
                paper_id="S2:1",
                title="Solid Electrolyte Discovery",
                doi="10.1000/example",
                cited_by_count=20,
                source_api="semantic_scholar",
                verified_by=["semantic_scholar"],
            )
        ],
    )
    arxiv = FakeClient(
        "arxiv",
        [
            Paper(
                paper_id="arxiv:2401.1",
                title="Another Solid Electrolyte Paper",
                arxiv_id="2401.00001v1",
                cited_by_count=0,
                source_api="arxiv",
                verified_by=["arxiv"],
            )
        ],
    )

    router = LiteratureRouter(
        Settings(),
        openalex=openalex,  # type: ignore[arg-type]
        semantic_scholar=semantic,  # type: ignore[arg-type]
        arxiv=arxiv,  # type: ignore[arg-type]
    )

    papers = await router.search(
        ["solid electrolyte"],
        max_papers=3,
        enable_semantic_scholar=True,
    )

    assert [paper.paper_id for paper in papers] == ["S2:1", "arxiv:2401.1"]
    assert papers[0].doi == "10.1000/example"
    assert set(papers[0].verified_by) == {"semantic_scholar", "openalex"}
    assert router.last_source_stats == {"openalex": 1, "semantic_scholar": 1, "arxiv": 1}


@pytest.mark.asyncio
async def test_literature_router_keeps_semantic_scholar_optional() -> None:
    openalex = FakeClient("openalex", [])
    semantic = FakeClient("semantic_scholar", [])
    arxiv = FakeClient("arxiv", [])
    router = LiteratureRouter(
        Settings(),
        openalex=openalex,  # type: ignore[arg-type]
        semantic_scholar=semantic,  # type: ignore[arg-type]
        arxiv=arxiv,  # type: ignore[arg-type]
    )

    await router.search(["query"], max_papers=2, enable_semantic_scholar=False)

    assert openalex.calls
    assert arxiv.calls
    assert semantic.calls == []


@pytest.mark.asyncio
async def test_literature_router_filters_irrelevant_high_citation_results() -> None:
    openalex = FakeClient(
        "openalex",
        [
            Paper(
                paper_id="W_irrelevant",
                title="Web Survey Methodology",
                abstract="A social science survey methods handbook.",
                cited_by_count=5000,
                source_api="openalex",
                verified_by=["openalex"],
            ),
            Paper(
                paper_id="W_relevant",
                title="Solid-state electrolyte ionic conductivity mechanisms",
                abstract="Solid electrolyte studies discuss lithium ion conductivity and transport pathways.",
                cited_by_count=50,
                source_api="openalex",
                verified_by=["openalex"],
            ),
        ],
    )
    semantic = FakeClient("semantic_scholar", [])
    arxiv = FakeClient("arxiv", [])
    router = LiteratureRouter(
        Settings(),
        openalex=openalex,  # type: ignore[arg-type]
        semantic_scholar=semantic,  # type: ignore[arg-type]
        arxiv=arxiv,  # type: ignore[arg-type]
    )

    papers = await router.search(
        [
            "solid-state electrolyte ionic conductivity mechanism",
            "structure property relationship solid electrolyte materials project",
        ],
        max_papers=2,
        enable_arxiv=False,
    )

    assert [paper.paper_id for paper in papers] == ["W_relevant"]
