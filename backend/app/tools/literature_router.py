import re
from collections.abc import Sequence

from app.config import Settings
from app.schemas.paper import Paper
from app.tools.arxiv_client import ArxivClient
from app.tools.crossref_client import CrossrefClient
from app.tools.openalex_client import OpenAlexClient
from app.tools.semantic_scholar_client import SemanticScholarClient


class LiteratureRouter:
    def __init__(
        self,
        settings: Settings,
        *,
        openalex: OpenAlexClient | None = None,
        crossref: CrossrefClient | None = None,
        semantic_scholar: SemanticScholarClient | None = None,
        arxiv: ArxivClient | None = None,
    ) -> None:
        self.settings = settings
        self.openalex = openalex or OpenAlexClient(settings)
        self.crossref = crossref
        self.semantic_scholar = semantic_scholar or SemanticScholarClient(settings)
        self.arxiv = arxiv or ArxivClient()
        self.last_source_stats: dict[str, int] = {}

    async def search(
        self,
        queries: Sequence[str],
        *,
        max_papers: int,
        enable_semantic_scholar: bool = False,
        enable_arxiv: bool = True,
        domain: str = "",
    ) -> list[Paper]:
        cleaned_queries = [query.strip() for query in queries if query.strip()]
        if not cleaned_queries or max_papers <= 0:
            self.last_source_stats = {}
            return []
        seismic_search = _is_seismic_search(domain, cleaned_queries)
        if seismic_search:
            cleaned_queries = _expand_seismic_queries(cleaned_queries)

        sources = ["openalex"]
        if self.crossref is not None:
            sources.append("crossref")
        if enable_semantic_scholar:
            sources.append("semantic_scholar")
        if enable_arxiv:
            sources.append("arxiv")

        per_source_limit = max(max_papers + 2, 8)
        candidates: list[Paper] = []
        stats = {source: 0 for source in sources}

        query_limit = 4 if seismic_search else 2
        for query in cleaned_queries[:query_limit]:
            for source in sources:
                papers = await self._search_source(source, query, per_source_limit)
                candidates.extend(papers)
                stats[source] += len(papers)

        deduped = _deduplicate(candidates)
        ranked = _rank_results(deduped, cleaned_queries, domain=domain)
        self.last_source_stats = {source: count for source, count in stats.items() if count > 0}
        return ranked[:max_papers]

    async def _search_source(self, source: str, query: str, limit: int) -> list[Paper]:
        try:
            if source == "openalex":
                return await self.openalex.search(query, limit)
            if source == "crossref" and self.crossref is not None:
                return await self.crossref.search(query, limit)
            if source == "semantic_scholar":
                return await self.semantic_scholar.search(query, limit)
            if source == "arxiv":
                return await self.arxiv.search(query, limit)
        except Exception:
            return []
        return []


def _deduplicate(papers: list[Paper]) -> list[Paper]:
    result: list[Paper] = []
    seen_doi: dict[str, int] = {}
    seen_arxiv: dict[str, int] = {}
    seen_title: dict[str, int] = {}

    def register(paper: Paper, index: int) -> None:
        if paper.doi:
            seen_doi[_norm_doi(paper.doi)] = index
        if paper.arxiv_id:
            seen_arxiv[_norm_arxiv_id(paper.arxiv_id)] = index
        title_key = _norm_title(paper.title)
        if title_key:
            seen_title[title_key] = index

    def replace(index: int, paper: Paper) -> None:
        result[index] = paper
        register(paper, index)

    for paper in papers:
        index = _find_existing_index(paper, seen_doi, seen_arxiv, seen_title)
        if index is None:
            register(paper, len(result))
            result.append(paper)
            continue

        old = result[index]
        if _rank(paper) > _rank(old):
            replace(index, _merge_metadata(old, paper))
        else:
            replace(index, _merge_metadata(paper, old))
    return result


def _find_existing_index(
    paper: Paper,
    seen_doi: dict[str, int],
    seen_arxiv: dict[str, int],
    seen_title: dict[str, int],
) -> int | None:
    if paper.doi:
        index = seen_doi.get(_norm_doi(paper.doi))
        if index is not None:
            return index
    if paper.arxiv_id:
        index = seen_arxiv.get(_norm_arxiv_id(paper.arxiv_id))
        if index is not None:
            return index
    title_key = _norm_title(paper.title)
    return seen_title.get(title_key) if title_key else None


def _merge_metadata(lower_priority: Paper, higher_priority: Paper) -> Paper:
    if not higher_priority.doi and lower_priority.doi:
        higher_priority.doi = lower_priority.doi
    if not higher_priority.arxiv_id and lower_priority.arxiv_id:
        higher_priority.arxiv_id = lower_priority.arxiv_id
    if not higher_priority.pdf_url and lower_priority.pdf_url:
        higher_priority.pdf_url = lower_priority.pdf_url
    if not higher_priority.source_url and lower_priority.source_url:
        higher_priority.source_url = lower_priority.source_url
    for source in lower_priority.verified_by:
        if source not in higher_priority.verified_by:
            higher_priority.verified_by.append(source)
    return higher_priority


def _rank(paper: Paper) -> tuple[int, int, int]:
    identifier_score = int(bool(paper.doi)) + int(bool(paper.arxiv_id))
    return (paper.cited_by_count or 0, paper.year or 0, identifier_score)


def _filter_relevant(papers: list[Paper], queries: Sequence[str]) -> list[Paper]:
    terms = _query_terms(queries)
    if len(terms) < 3:
        return papers
    return [paper for paper in papers if _relevance_score(paper, queries) > 0]


def _rank_results(papers: list[Paper], queries: Sequence[str], *, domain: str = "") -> list[Paper]:
    if _is_seismic_search(domain, queries):
        return _rank_seismic_results(papers, queries)

    relevant = _filter_relevant(papers, queries)
    ranked = relevant if relevant else papers
    ranked.sort(
        key=lambda paper: (
            _relevance_score(paper, queries),
            paper.cited_by_count or 0,
            paper.year or 0,
        ),
        reverse=True,
    )
    return ranked


def _relevance_score(paper: Paper, queries: Sequence[str]) -> int:
    terms = _query_terms(queries)
    if len(terms) < 3:
        return 1
    text = _paper_text(paper)
    return sum(1 for term in terms if term in text)


def _paper_text(paper: Paper) -> str:
    return " ".join(
        [
            paper.title or "",
            paper.abstract or "",
            paper.venue or "",
        ]
    ).lower()


def _is_seismic_search(domain: str, queries: Sequence[str]) -> bool:
    if domain == "seismic_event_classification":
        return True
    text = " ".join(queries).lower()
    return any(term in text for term in _SEISMIC_QUERY_HINTS)


def _expand_seismic_queries(queries: Sequence[str]) -> list[str]:
    expanded: list[str] = []
    for query in [*_SEISMIC_PRIORITY_QUERIES, *queries]:
        cleaned = query.strip()
        if cleaned and cleaned.lower() not in {item.lower() for item in expanded}:
            expanded.append(cleaned)
    return expanded


def _rank_seismic_results(papers: list[Paper], queries: Sequence[str]) -> list[Paper]:
    if not papers:
        return []

    def key(paper: Paper) -> tuple[int, int, int, int]:
        return (
            _seismic_relevance_score(paper),
            _relevance_score(paper, queries),
            paper.cited_by_count or 0,
            paper.year or 0,
        )

    seismic = [paper for paper in papers if _seismic_relevance_score(paper) > 0]
    off_topic = [paper for paper in papers if _seismic_relevance_score(paper) <= 0]
    if not seismic:
        return sorted(papers, key=key, reverse=True)
    return sorted(seismic, key=key, reverse=True) + sorted(off_topic, key=key, reverse=True)


def _seismic_relevance_score(paper: Paper) -> int:
    text = _paper_text(paper)
    negative = sum(1 for term in _SEISMIC_NEGATIVE_TERMS if term in text)
    anchor_hits = sum(1 for term in _SEISMIC_ANCHOR_TERMS if term in text)
    if anchor_hits == 0:
        return -4 * negative

    score = anchor_hits * 2
    score += sum(3 for phrase in _SEISMIC_STRONG_PHRASES if phrase in text)
    score += sum(1 for term in _SEISMIC_METHOD_TERMS if term in text)
    score -= 4 * negative
    return score


def _query_terms(queries: Sequence[str]) -> set[str]:
    text = " ".join(queries).lower()
    words = re.findall(r"[a-z][a-z0-9-]{3,}", text)
    return {word.strip("-") for word in words if word not in _QUERY_STOPWORDS}


def _norm_doi(value: str) -> str:
    doi = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            return doi[len(prefix):]
    return doi


def _norm_arxiv_id(value: str) -> str:
    return re.sub(r"v\d+$", "", value.strip().lower())


def _norm_title(value: str) -> str:
    text = re.sub(r"[^a-z0-9\s]", "", value.lower())
    return re.sub(r"\s+", " ", text).strip()


_QUERY_STOPWORDS = {
    "based",
    "baseline",
    "bounded",
    "candidate",
    "data",
    "database",
    "dataset",
    "datasets",
    "design",
    "evidence",
    "experiment",
    "generate",
    "hypothesis",
    "literature",
    "materials",
    "mechanism",
    "open",
    "plan",
    "property",
    "recent",
    "research",
    "review",
    "source",
    "study",
    "verifiable",
    "with",
}

_SEISMIC_QUERY_HINTS = (
    "seismic",
    "earthquake",
    "seismology",
    "seismogram",
    "waveform",
    "phasenet",
    "eqtransformer",
    "seisbench",
    "stead",
    "microseismic",
)

_SEISMIC_PRIORITY_QUERIES = (
    "seismic event classification deep learning waveform",
    "earthquake explosion discrimination waveform classification deep learning",
    "seismic phase picking phase classification PhaseNet EQTransformer",
    "earthquake detection seismic waveform CNN transformer",
)

_SEISMIC_ANCHOR_TERMS = (
    "seismic",
    "earthquake",
    "quake",
    "seismology",
    "seismogram",
    "waveform",
    "microseismic",
    "phasenet",
    "eqtransformer",
    "eq transformer",
    "seisbench",
    "stead",
    "obspy",
    "blast",
    "quarry",
)

_SEISMIC_STRONG_PHRASES = (
    "seismic event classification",
    "seismic event detection",
    "earthquake detection",
    "earthquake classification",
    "earthquake explosion",
    "earthquake-explosion",
    "explosion discrimination",
    "phase picking",
    "phase-picking",
    "phase classification",
    "seismic phase",
    "seismic waveform",
    "waveform classification",
    "microseismic event",
)

_SEISMIC_METHOD_TERMS = (
    "deep learning",
    "neural",
    "cnn",
    "convolutional",
    "transformer",
    "resnet",
    "model",
    "method",
    "classification",
    "detection",
    "picker",
    "benchmark",
)

_SEISMIC_NEGATIVE_TERMS = (
    "covid",
    "sentiment",
    "recommender",
    "recommendation",
    "thrombectomy",
    "ct imaging",
    "stroke",
    "medical",
    "xray",
    "x-ray",
    "lung",
    "tumor",
    "cancer",
    "volcanic ash",
    "gaussian radial basis",
    "active subspace",
    "polynomial chaos",
    "mathematics of deep learning",
)
