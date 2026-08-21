from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.schemas.citation import CitationVerificationReport, CitationVerificationResult
from app.schemas.paper import Paper
from app.tools.arxiv_client import ArxivClient
from app.tools.citation_verifier import (
    SUSPICIOUS_THRESHOLD,
    _apply_result,
    _best_partial,
    _build_report,
    _result,
    _title_result,
    _title_similarity,
)
from app.tools.crossref_client import CrossrefClient
from app.tools.literature_router import (
    _deduplicate,
    _expand_seismic_queries,
    _is_seismic_search,
    _rank_results,
)
from app.tools.openalex_client import OpenAlexClient


class LiteratureSearchInput(BaseModel):
    query: str = Field(..., description="Scholarly search query.")
    limit: int = Field(5, ge=1, le=100, description="Maximum number of papers to return.")


class CrossrefVerifyInput(BaseModel):
    paper: dict[str, Any] = Field(..., description="Paper metadata to verify against Crossref.")


def build_openalex_search_tool(openalex: OpenAlexClient) -> StructuredTool:
    async def _search(query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = await openalex.search(query, limit)
        return [paper.model_dump(mode="json") for paper in papers]

    return StructuredTool.from_function(
        coroutine=_search,
        name="openalex_search",
        description="Search OpenAlex works and return normalized TrustSci paper metadata.",
        args_schema=LiteratureSearchInput,
    )


def build_arxiv_search_tool(arxiv: ArxivClient) -> StructuredTool:
    async def _search(query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = await arxiv.search(query, limit)
        return [paper.model_dump(mode="json") for paper in papers]

    return StructuredTool.from_function(
        coroutine=_search,
        name="arxiv_search",
        description="Search arXiv and return normalized TrustSci paper metadata.",
        args_schema=LiteratureSearchInput,
    )


def build_crossref_search_tool(crossref: CrossrefClient) -> StructuredTool:
    async def _search(query: str, limit: int = 5) -> list[dict[str, Any]]:
        papers = await crossref.search(query, limit)
        return [paper.model_dump(mode="json") for paper in papers]

    return StructuredTool.from_function(
        coroutine=_search,
        name="crossref_search",
        description="Search Crossref works and return normalized TrustSci paper metadata, including DOI metadata for IEEE/Elsevier/Springer/AGU/SSA publications.",
        args_schema=LiteratureSearchInput,
    )


def build_crossref_verify_tool(crossref: CrossrefClient) -> StructuredTool:
    async def _verify(paper: dict[str, Any]) -> dict[str, Any]:
        verified = await crossref.verify(Paper.model_validate(paper))
        return verified.model_dump(mode="json")

    return StructuredTool.from_function(
        coroutine=_verify,
        name="crossref_verify",
        description="Verify DOI, title, year, and bibliographic metadata against Crossref.",
        args_schema=CrossrefVerifyInput,
    )


async def search_literature_with_tools(
    *,
    queries: list[str],
    max_papers: int,
    openalex_search_tool: StructuredTool,
    arxiv_search_tool: StructuredTool,
    crossref_search_tool: StructuredTool | None = None,
    enable_arxiv: bool = True,
    domain: str = "",
) -> tuple[list[Paper], dict[str, int]]:
    cleaned_queries = [query.strip() for query in queries if query.strip()]
    if not cleaned_queries or max_papers <= 0:
        return [], {}
    seismic_search = _is_seismic_search(domain, cleaned_queries)
    if seismic_search:
        cleaned_queries = _expand_seismic_queries(cleaned_queries)

    sources: list[tuple[str, StructuredTool]] = [("openalex", openalex_search_tool)]
    if crossref_search_tool is not None:
        sources.append(("crossref", crossref_search_tool))
    if enable_arxiv:
        sources.append(("arxiv", arxiv_search_tool))

    # Keep the LangGraph tool path aligned with LiteratureRouter: fetch a
    # larger per-source candidate pool, then rank and truncate globally.
    per_source_limit = max(max_papers + 2, 8)
    candidates: list[Paper] = []
    stats = {source: 0 for source, _tool in sources}

    query_limit = 4 if seismic_search else 2
    for query in cleaned_queries[:query_limit]:
        for source, tool in sources:
            papers = await _invoke_search_tool(tool, query=query, limit=per_source_limit)
            candidates.extend(papers)
            stats[source] += len(papers)

    deduped = _deduplicate(candidates)
    ranked = _rank_results(deduped, cleaned_queries, domain=domain)
    return ranked[:max_papers], {source: count for source, count in stats.items() if count > 0}


async def verify_citations_with_tools(
    *,
    papers: list[Paper],
    openalex_search_tool: StructuredTool,
    arxiv_search_tool: StructuredTool,
    crossref_verify_tool: StructuredTool,
) -> tuple[list[Paper], CitationVerificationReport]:
    results: list[CitationVerificationResult] = []
    verified_papers: list[Paper] = []

    for paper in papers:
        verified_paper, result = await _verify_paper_with_tools(
            paper,
            openalex_search_tool=openalex_search_tool,
            arxiv_search_tool=arxiv_search_tool,
            crossref_verify_tool=crossref_verify_tool,
        )
        _apply_result(verified_paper, result)
        results.append(result)
        verified_papers.append(verified_paper)

    return verified_papers, _build_report(results)


async def _invoke_search_tool(tool: StructuredTool, *, query: str, limit: int) -> list[Paper]:
    try:
        raw_papers = await tool.ainvoke({"query": query, "limit": limit})
    except Exception:
        return []
    if not isinstance(raw_papers, list):
        return []
    papers: list[Paper] = []
    for item in raw_papers:
        try:
            papers.append(Paper.model_validate(item))
        except Exception:
            continue
    return papers


async def _verify_paper_with_tools(
    paper: Paper,
    *,
    openalex_search_tool: StructuredTool,
    arxiv_search_tool: StructuredTool,
    crossref_verify_tool: StructuredTool,
) -> tuple[Paper, CitationVerificationResult]:
    if not paper.title.strip():
        return paper, _result(paper, "skipped", 0.0, "skipped", "Paper has no title.")

    current = paper.model_copy(deep=True)
    best_partial: CitationVerificationResult | None = None

    if current.doi:
        crossref_paper, crossref_result = await _verify_crossref_with_tool(current, crossref_verify_tool)
        current = crossref_paper
        if crossref_result and crossref_result.status == "verified":
            return current, crossref_result
        best_partial = _best_partial(best_partial, crossref_result)

    openalex_result = await _verify_title_with_search_tool(current, openalex_search_tool, "openalex")
    if openalex_result and openalex_result.status == "verified":
        return current, openalex_result
    best_partial = _best_partial(best_partial, openalex_result)

    arxiv_result = await _verify_title_with_search_tool(current, arxiv_search_tool, "arxiv")
    if arxiv_result and arxiv_result.status == "verified":
        return current, arxiv_result
    best_partial = _best_partial(best_partial, arxiv_result)

    if best_partial is not None:
        return current, best_partial
    return current, _result(
        current,
        "hallucinated",
        0.0,
        "langchain_tools",
        "No matching DOI, OpenAlex title, or arXiv title result was found.",
    )


async def _verify_crossref_with_tool(
    paper: Paper,
    crossref_verify_tool: StructuredTool,
) -> tuple[Paper, CitationVerificationResult | None]:
    try:
        raw = await crossref_verify_tool.ainvoke({"paper": paper.model_dump(mode="json")})
        verified = Paper.model_validate(raw)
    except Exception:
        return paper, None

    score = verified.title_match_score or 0.0
    matched_source = verified.source_url or (f"https://doi.org/{verified.doi}" if verified.doi else None)
    if verified.verification_status == "verified":
        return verified, _result(
            verified,
            "verified",
            score or 0.85,
            "crossref_tool_doi",
            "DOI and title/year metadata matched Crossref through a LangChain Tool.",
            matched_source=matched_source,
        )
    if score >= SUSPICIOUS_THRESHOLD:
        return verified, _result(
            verified,
            "suspicious",
            score,
            "crossref_tool_doi",
            "DOI exists in Crossref but title/year metadata is only a partial match.",
            matched_source=matched_source,
        )
    return verified, None


async def _verify_title_with_search_tool(
    paper: Paper,
    search_tool: StructuredTool,
    source: str,
) -> CitationVerificationResult | None:
    candidates = await _invoke_search_tool(search_tool, query=paper.title, limit=5)
    if not candidates:
        return None
    best = max(candidates, key=lambda item: _title_similarity(paper.title, item.title))
    if best.doi and not paper.doi:
        paper.doi = best.doi
    if best.arxiv_id and not paper.arxiv_id:
        paper.arxiv_id = best.arxiv_id
    return _title_result(paper, best.title, f"{source}_tool_title", source, best.source_url)
