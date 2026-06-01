import html
import re
from typing import Any

import httpx

from app.config import Settings
from app.schemas.paper import Paper


SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = ",".join(
    [
        "paperId",
        "externalIds",
        "url",
        "title",
        "authors",
        "year",
        "publicationDate",
        "venue",
        "abstract",
        "citationCount",
        "openAccessPdf",
        "isOpenAccess",
        "fieldsOfStudy",
        "publicationTypes",
    ]
)


class SemanticScholarClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    async def search(self, query: str, limit: int) -> list[Paper]:
        query = query.strip()
        if not query or limit <= 0:
            return []

        params: dict[str, str | int] = {
            "query": query,
            "limit": max(1, min(limit, 100)),
            "fields": SEMANTIC_SCHOLAR_FIELDS,
        }
        headers = self._headers()
        try:
            async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
                response = await client.get(SEMANTIC_SCHOLAR_SEARCH_URL, params=params, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError:
            return []
        data = response.json().get("data", [])

        papers: list[Paper] = []
        for item in data:
            paper = _paper_from_item(item, len(papers) + 1)
            if paper is not None:
                papers.append(paper)
            if len(papers) >= limit:
                break
        return papers

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": "TrustSci-Agent/0.1"}
        if self.settings.semantic_scholar_api_key:
            headers["x-api-key"] = self.settings.semantic_scholar_api_key
        return headers


def _paper_from_item(item: dict[str, Any], index: int) -> Paper | None:
    title = _clean_text(item.get("title"))
    if not title:
        return None

    external_ids = item.get("externalIds") or {}
    paper_id = item.get("paperId")
    open_access_pdf = item.get("openAccessPdf") or {}
    publication_types = item.get("publicationTypes") or []

    return Paper(
        paper_id=f"S2:{paper_id}" if paper_id else f"semantic_scholar_{index:03d}",
        title=title,
        authors=_authors(item.get("authors")),
        year=item.get("year"),
        publication_date=item.get("publicationDate"),
        doi=_normalize_doi(external_ids.get("DOI")),
        semantic_scholar_id=paper_id,
        source_url=item.get("url"),
        pdf_url=open_access_pdf.get("url"),
        abstract=_clean_text(item.get("abstract")),
        venue=_clean_text(item.get("venue")) or None,
        work_type=publication_types[0] if publication_types else None,
        cited_by_count=item.get("citationCount"),
        fields_of_study=[str(field) for field in item.get("fieldsOfStudy") or []],
        is_open_access=item.get("isOpenAccess"),
        source_api="semantic_scholar",
        verified_by=["semantic_scholar"],
        verification_status="candidate",
    )


def _authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get("name"))
        if name:
            names.append(name)
    return names


def _normalize_doi(raw: object) -> str | None:
    if not raw:
        return None
    doi = str(raw).strip()
    lower = doi.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lower.startswith(prefix):
            return doi[len(prefix):]
    return doi


def _clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()
