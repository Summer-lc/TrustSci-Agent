import html
import re
from typing import Any
from urllib.parse import quote

import httpx
from rapidfuzz import fuzz

from app.config import Settings
from app.schemas.citation import CitationVerificationReport, CitationVerificationResult
from app.schemas.paper import Paper
from app.tools.arxiv_client import ArxivClient
from app.tools.crossref_client import CrossrefClient
from app.tools.openalex_client import OpenAlexClient
from app.tools.semantic_scholar_client import SemanticScholarClient


DATACITE_DOI_URL = "https://api.datacite.org/dois"
VERIFIED_THRESHOLD = 0.82
SUSPICIOUS_THRESHOLD = 0.50


class CitationVerifier:
    def __init__(
        self,
        settings: Settings,
        *,
        crossref: CrossrefClient | None = None,
        openalex: OpenAlexClient | None = None,
        semantic_scholar: SemanticScholarClient | None = None,
        arxiv: ArxivClient | None = None,
        datacite_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.crossref = crossref or CrossrefClient(settings)
        self.openalex = openalex or OpenAlexClient(settings)
        self.semantic_scholar = semantic_scholar or SemanticScholarClient(settings)
        self.arxiv = arxiv or ArxivClient()
        self.datacite_transport = datacite_transport

    async def verify_many(
        self,
        papers: list[Paper],
        *,
        enable_semantic_scholar: bool = False,
    ) -> tuple[list[Paper], CitationVerificationReport]:
        results: list[CitationVerificationResult] = []
        verified_papers: list[Paper] = []
        for paper in papers:
            result = await self.verify(paper, enable_semantic_scholar=enable_semantic_scholar)
            _apply_result(paper, result)
            results.append(result)
            verified_papers.append(paper)
        return verified_papers, _build_report(results)

    async def verify(self, paper: Paper, *, enable_semantic_scholar: bool = False) -> CitationVerificationResult:
        if not paper.title.strip():
            return _result(paper, "skipped", 0.0, "skipped", "Paper has no title.")

        best_partial: CitationVerificationResult | None = None

        if paper.arxiv_id:
            arxiv_result = await self._verify_arxiv_id(paper)
            if arxiv_result and arxiv_result.status == "verified":
                return arxiv_result
            best_partial = _best_partial(best_partial, arxiv_result)

        if paper.doi:
            crossref_result = await self._verify_crossref(paper)
            if crossref_result and crossref_result.status == "verified":
                return crossref_result
            best_partial = _best_partial(best_partial, crossref_result)

            datacite_result = await self._verify_datacite(paper)
            if datacite_result and datacite_result.status == "verified":
                return datacite_result
            best_partial = _best_partial(best_partial, datacite_result)

        openalex_result = await self._verify_title_search(paper, "openalex")
        if openalex_result and openalex_result.status == "verified":
            return openalex_result
        best_partial = _best_partial(best_partial, openalex_result)

        if enable_semantic_scholar:
            s2_result = await self._verify_title_search(paper, "semantic_scholar")
            if s2_result and s2_result.status == "verified":
                return s2_result
            best_partial = _best_partial(best_partial, s2_result)

        arxiv_title_result = await self._verify_title_search(paper, "arxiv")
        if arxiv_title_result and arxiv_title_result.status == "verified":
            return arxiv_title_result
        best_partial = _best_partial(best_partial, arxiv_title_result)

        if best_partial is not None:
            return best_partial
        return _result(
            paper,
            "hallucinated",
            0.0,
            "multi_source",
            "No matching DOI, arXiv ID, or title result was found.",
        )

    async def _verify_arxiv_id(self, paper: Paper) -> CitationVerificationResult | None:
        if not paper.arxiv_id:
            return None
        match = await self.arxiv.get_by_id(paper.arxiv_id)
        if match is None:
            return _result(paper, "hallucinated", 0.9, "arxiv_id", f"arXiv ID {paper.arxiv_id} was not found.")
        return _title_result(paper, match.title, "arxiv_id", "arxiv", match.source_url)

    async def _verify_crossref(self, paper: Paper) -> CitationVerificationResult | None:
        before_status = paper.verification_status
        verified = await self.crossref.verify(paper)
        score = verified.title_match_score or 0.0
        if verified.verification_status == "verified":
            return _result(
                paper,
                "verified",
                score or 0.85,
                "crossref_doi",
                "DOI and title/year metadata matched Crossref.",
                matched_source=paper.source_url or (f"https://doi.org/{paper.doi}" if paper.doi else None),
            )
        if score >= SUSPICIOUS_THRESHOLD:
            return _result(
                paper,
                "suspicious",
                score,
                "crossref_doi",
                "DOI exists in Crossref but title/year metadata is only a partial match.",
                matched_source=paper.source_url or (f"https://doi.org/{paper.doi}" if paper.doi else None),
            )
        paper.verification_status = before_status
        return None

    async def _verify_datacite(self, paper: Paper) -> CitationVerificationResult | None:
        if not paper.doi:
            return None
        try:
            async with httpx.AsyncClient(timeout=20, transport=self.datacite_transport) as client:
                response = await client.get(
                    f"{DATACITE_DOI_URL}/{quote(paper.doi, safe='')}",
                    headers={"User-Agent": "TrustSci-Agent/0.1", "Accept": "application/json"},
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
        except httpx.HTTPError:
            return None

        attrs = response.json().get("data", {}).get("attributes", {})
        titles = attrs.get("titles") or []
        found_title = _clean_text(titles[0].get("title")) if titles and isinstance(titles[0], dict) else ""
        if not found_title:
            return _result(
                paper,
                "verified",
                0.85,
                "datacite_doi",
                "DOI resolves via DataCite; title metadata was not available.",
                matched_source=f"https://doi.org/{paper.doi}",
            )
        return _title_result(paper, found_title, "datacite_doi", "datacite", f"https://doi.org/{paper.doi}")

    async def _verify_title_search(self, paper: Paper, source: str) -> CitationVerificationResult | None:
        try:
            if source == "openalex":
                candidates = await self.openalex.search(paper.title, 5)
            elif source == "semantic_scholar":
                candidates = await self.semantic_scholar.search(paper.title, 5)
            elif source == "arxiv":
                candidates = await self.arxiv.search(paper.title, 5)
            else:
                candidates = []
        except Exception:
            return None
        if not candidates:
            return None
        best = max(candidates, key=lambda item: _title_similarity(paper.title, item.title))
        result = _title_result(paper, best.title, f"{source}_title", source, best.source_url)
        if best.doi and not paper.doi:
            paper.doi = best.doi
        if best.arxiv_id and not paper.arxiv_id:
            paper.arxiv_id = best.arxiv_id
        return result


def _title_result(
    paper: Paper,
    found_title: str,
    method: str,
    source: str,
    matched_source: str | None,
) -> CitationVerificationResult:
    score = _title_similarity(paper.title, found_title)
    if score >= VERIFIED_THRESHOLD:
        status = "verified"
        details = f"Title matched {source}: {found_title}"
    elif score >= SUSPICIOUS_THRESHOLD:
        status = "suspicious"
        details = f"Partial title match via {source}: {found_title}"
    else:
        status = "hallucinated"
        details = f"No close title match via {source}; best candidate: {found_title}"
    return _result(paper, status, score, method, details, matched_source=matched_source)


def _result(
    paper: Paper,
    status: str,
    confidence: float,
    method: str,
    details: str,
    *,
    matched_source: str | None = None,
) -> CitationVerificationResult:
    return CitationVerificationResult(
        paper_id=paper.paper_id,
        title=paper.title,
        status=status,
        confidence=round(confidence, 3),
        method=method,
        details=details,
        matched_source=matched_source,
        doi=paper.doi,
        source_api=paper.source_api,
    )


def _apply_result(paper: Paper, result: CitationVerificationResult) -> None:
    paper.verification_status = result.status
    paper.verification_method = result.method
    paper.verification_confidence = result.confidence
    paper.matched_source = result.matched_source
    paper.report_eligible = result.status == "verified"
    if result.confidence:
        paper.title_match_score = result.confidence
    provider = _provider_from_method(result.method)
    if provider and provider not in paper.verified_by:
        paper.verified_by.append(provider)


def _build_report(results: list[CitationVerificationResult]) -> CitationVerificationReport:
    total = len(results)
    verified = len([item for item in results if item.status == "verified"])
    suspicious = len([item for item in results if item.status == "suspicious"])
    hallucinated = len([item for item in results if item.status == "hallucinated"])
    skipped = len([item for item in results if item.status == "skipped"])
    verifiable = total - skipped
    integrity_score = round(verified / verifiable, 3) if verifiable > 0 else 1.0
    return CitationVerificationReport(
        total=total,
        verified=verified,
        suspicious=suspicious,
        hallucinated=hallucinated,
        skipped=skipped,
        integrity_score=integrity_score,
        results=results,
    )


def _best_partial(
    current: CitationVerificationResult | None,
    candidate: CitationVerificationResult | None,
) -> CitationVerificationResult | None:
    if candidate is None:
        return current
    if candidate.status == "suspicious":
        if current is None or candidate.confidence > current.confidence:
            return candidate
    return current


def _title_similarity(a: str, b: str) -> float:
    if not a.strip() or not b.strip():
        return 0.0
    return round(fuzz.token_sort_ratio(a, b) / 100, 3)


def _provider_from_method(method: str) -> str:
    if method.startswith("semantic_scholar"):
        return "semantic_scholar"
    if method.startswith("crossref"):
        return "crossref"
    if method.startswith("datacite"):
        return "datacite"
    if method.startswith("openalex"):
        return "openalex"
    if method.startswith("arxiv"):
        return "arxiv"
    return method


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()
