import html
import re
from typing import Any

import httpx

from app.config import Settings
from app.schemas.paper import Paper


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
WORK_SELECT_FIELDS = ",".join(
    [
        "id",
        "doi",
        "display_name",
        "publication_year",
        "publication_date",
        "type",
        "cited_by_count",
        "is_retracted",
        "is_paratext",
        "authorships",
        "primary_location",
        "best_oa_location",
        "open_access",
        "abstract_inverted_index",
    ]
)


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in index.items():
        for position in indexes:
            positions.append((position, word))
    return _clean_text(" ".join(word for _, word in sorted(positions)))


class OpenAlexClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    async def search(self, query: str, limit: int) -> list[Paper]:
        query = query.strip()
        if not query or limit <= 0:
            return []
        params: dict[str, str | int] = {
            "search": query,
            "per-page": max(1, min(limit, 100)),
            "filter": "is_retracted:false,is_paratext:false",
            "select": WORK_SELECT_FIELDS,
        }
        if self.settings.openalex_email:
            params["mailto"] = self.settings.openalex_email

        async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
            response = await client.get(OPENALEX_WORKS_URL, params=params)
            response.raise_for_status()
        results = response.json().get("results", [])

        papers: list[Paper] = []
        for item in results:
            paper = _paper_from_work(item, len(papers) + 1)
            if paper is not None:
                papers.append(paper)
            if len(papers) >= limit:
                break
        return papers


def _paper_from_work(item: dict[str, Any], index: int) -> Paper | None:
    if item.get("is_retracted") or item.get("is_paratext"):
        return None
    title = _clean_text(item.get("display_name"))
    if not title:
        return None

    primary_location = item.get("primary_location") or {}
    best_oa_location = item.get("best_oa_location") or {}
    open_access = item.get("open_access") or {}
    source = primary_location.get("source") or best_oa_location.get("source") or {}
    openalex_id = item.get("id")
    doi = _normalize_doi(item.get("doi"))

    pdf_url = (
        best_oa_location.get("pdf_url")
        or primary_location.get("pdf_url")
        or open_access.get("oa_url")
    )
    source_url = (
        primary_location.get("landing_page_url")
        or best_oa_location.get("landing_page_url")
        or open_access.get("oa_url")
        or openalex_id
    )

    authors = [
        name
        for name in (
            (authorship.get("author") or {}).get("display_name", "")
            for authorship in item.get("authorships", [])
            if isinstance(authorship, dict)
        )
        if name
    ]

    return Paper(
        paper_id=_paper_id(openalex_id, index),
        title=title,
        authors=authors,
        year=item.get("publication_year"),
        publication_date=item.get("publication_date"),
        doi=doi,
        openalex_id=openalex_id,
        source_url=source_url,
        pdf_url=pdf_url,
        abstract=_abstract_from_inverted_index(item.get("abstract_inverted_index")),
        venue=_clean_text(source.get("display_name")) or None,
        work_type=item.get("type"),
        cited_by_count=item.get("cited_by_count"),
        is_open_access=open_access.get("is_oa"),
        is_retracted=bool(item.get("is_retracted")),
        source_api="openalex",
        verified_by=["openalex"],
        verification_status="candidate",
    )


def _paper_id(openalex_id: str | None, index: int) -> str:
    if openalex_id:
        return openalex_id.rstrip("/").split("/")[-1]
    return f"openalex_{index:03d}"


def _normalize_doi(raw: str | None) -> str | None:
    if not raw:
        return None
    doi = raw.strip()
    prefixes = ("https://doi.org/", "http://doi.org/", "doi:")
    lower = doi.lower()
    for prefix in prefixes:
        if lower.startswith(prefix):
            return doi[len(prefix):]
    return doi


def _clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()
