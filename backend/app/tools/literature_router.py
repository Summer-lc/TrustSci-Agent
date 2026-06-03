import re
from collections.abc import Sequence

from app.config import Settings
from app.schemas.paper import Paper
from app.tools.arxiv_client import ArxivClient
from app.tools.openalex_client import OpenAlexClient
from app.tools.semantic_scholar_client import SemanticScholarClient


class LiteratureRouter:
    def __init__(
        self,
        settings: Settings,
        *,
        openalex: OpenAlexClient | None = None,
        semantic_scholar: SemanticScholarClient | None = None,
        arxiv: ArxivClient | None = None,
    ) -> None:
        self.settings = settings
        self.openalex = openalex or OpenAlexClient(settings)
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
    ) -> list[Paper]:
        cleaned_queries = [query.strip() for query in queries if query.strip()]
        if not cleaned_queries or max_papers <= 0:
            self.last_source_stats = {}
            return []

        sources = ["openalex"]
        if enable_semantic_scholar:
            sources.append("semantic_scholar")
        if enable_arxiv:
            sources.append("arxiv")

        per_source_limit = max(1, min(max_papers, max_papers // len(sources) + 1))
        candidates: list[Paper] = []
        stats = {source: 0 for source in sources}

        for query in cleaned_queries[:2]:
            for source in sources:
                papers = await self._search_source(source, query, per_source_limit)
                candidates.extend(papers)
                stats[source] += len(papers)

        deduped = _deduplicate(candidates)
        deduped.sort(key=lambda paper: (paper.cited_by_count or 0, paper.year or 0), reverse=True)
        self.last_source_stats = {source: count for source, count in stats.items() if count > 0}
        return deduped[:max_papers]

    async def _search_source(self, source: str, query: str, limit: int) -> list[Paper]:
        try:
            if source == "openalex":
                return await self.openalex.search(query, limit)
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
