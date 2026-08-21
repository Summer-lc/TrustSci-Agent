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


@pytest.mark.asyncio
async def test_literature_router_prioritizes_seismic_queries_for_seismic_domain() -> None:
    openalex = FakeClient("openalex", [])
    semantic = FakeClient("semantic_scholar", [])
    arxiv = FakeClient("arxiv", [])
    router = LiteratureRouter(
        Settings(),
        openalex=openalex,  # type: ignore[arg-type]
        semantic_scholar=semantic,  # type: ignore[arg-type]
        arxiv=arxiv,  # type: ignore[arg-type]
    )

    await router.search(
        ["generic deep learning classification"],
        max_papers=3,
        enable_arxiv=False,
        domain="seismic_event_classification",
    )

    assert openalex.calls[0][0] == "seismic event classification deep learning waveform"
    assert len(openalex.calls) == 4


@pytest.mark.asyncio
async def test_literature_router_ranks_seismic_papers_above_generic_cross_domain_results() -> None:
    openalex = FakeClient(
        "openalex",
        [
            Paper(
                paper_id="medical",
                title="Predicting Thrombectomy Recanalization from CT Imaging Using Deep Learning Models",
                abstract="A medical CT imaging study for acute ischemic stroke.",
                cited_by_count=500,
                source_api="openalex",
                verified_by=["openalex"],
            ),
            Paper(
                paper_id="seismic_detection",
                title="Deep Learning-based Small Magnitude Earthquake Detection and Seismic Phase Classification",
                abstract="A seismic waveform method for earthquake detection and phase classification.",
                cited_by_count=10,
                source_api="openalex",
                verified_by=["openalex"],
            ),
            Paper(
                paper_id="volcanic_ash",
                title="Classification of volcanic ash particles using a convolutional neural network",
                abstract="Volcanic ash particles are classified from images.",
                cited_by_count=300,
                source_api="openalex",
                verified_by=["openalex"],
            ),
            Paper(
                paper_id="blast",
                title="Earthquake and quarry blast discrimination using waveform deep learning",
                abstract="Seismic waveform classification distinguishes earthquake and blast events.",
                cited_by_count=5,
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
        ["deep learning classification"],
        max_papers=4,
        enable_arxiv=False,
        domain="seismic_event_classification",
    )

    assert [paper.paper_id for paper in papers[:2]] == ["seismic_detection", "blast"]
    assert "medical" not in [paper.paper_id for paper in papers[:2]]
    assert "volcanic_ash" not in [paper.paper_id for paper in papers[:2]]


@pytest.mark.asyncio
async def test_literature_router_uses_crossref_as_journal_fallback_for_seismic_domain() -> None:
    openalex = FakeClient("openalex", [])
    crossref = FakeClient(
        "crossref",
        [
            Paper(
                paper_id="crossref:ieee_seismic",
                title="Deep learning for seismic event classification in earthquake monitoring",
                abstract="A seismic waveform classification method published in an IEEE journal.",
                doi="10.1109/example",
                source_api="crossref",
                verified_by=["crossref"],
            )
        ],
    )
    semantic = FakeClient("semantic_scholar", [])
    arxiv = FakeClient("arxiv", [])
    router = LiteratureRouter(
        Settings(),
        openalex=openalex,  # type: ignore[arg-type]
        crossref=crossref,  # type: ignore[arg-type]
        semantic_scholar=semantic,  # type: ignore[arg-type]
        arxiv=arxiv,  # type: ignore[arg-type]
    )

    papers = await router.search(
        ["seismic event classification"],
        max_papers=3,
        enable_arxiv=True,
        domain="seismic_event_classification",
    )

    assert [paper.paper_id for paper in papers] == ["crossref:ieee_seismic"]
    assert router.last_source_stats == {"crossref": 4}
