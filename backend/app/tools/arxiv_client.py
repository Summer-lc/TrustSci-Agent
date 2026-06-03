import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from app.schemas.paper import Paper


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArxivClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def search(self, query: str, limit: int) -> list[Paper]:
        query = query.strip()
        if not query or limit <= 0:
            return []
        params: dict[str, str | int] = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max(1, min(limit, 50)),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        return await self._query(params, limit)

    async def get_by_id(self, arxiv_id: str) -> Paper | None:
        arxiv_id = arxiv_id.strip()
        if not arxiv_id:
            return None
        papers = await self._query({"id_list": arxiv_id, "max_results": 1}, 1)
        return papers[0] if papers else None

    async def _query(self, params: dict[str, str | int], limit: int) -> list[Paper]:
        try:
            async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
                response = await client.get(
                    ARXIV_API_URL,
                    params=params,
                    headers={"User-Agent": "TrustSci-Agent/0.1"},
                )
                response.raise_for_status()
        except httpx.HTTPError:
            return []

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return []

        papers: list[Paper] = []
        for entry in root.findall("atom:entry", ARXIV_NS):
            paper = _paper_from_entry(entry)
            if paper is not None:
                papers.append(paper)
            if len(papers) >= limit:
                break
        return papers


def _paper_from_entry(entry: ET.Element) -> Paper | None:
    entry_id = _text(entry, "atom:id")
    if "api/errors" in entry_id:
        return None

    title = _clean_text(_text(entry, "atom:title"))
    if not title:
        return None

    arxiv_id = _extract_arxiv_id(entry_id)
    pdf_url = _pdf_url(entry)
    abs_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else entry_id or None
    doi = _normalize_doi(_text(entry, "arxiv:doi"))
    published = _text(entry, "atom:published")

    return Paper(
        paper_id=f"arxiv:{arxiv_id}" if arxiv_id else f"arxiv:{_slug(title)}",
        title=title,
        authors=_authors(entry),
        year=_year(published),
        publication_date=published[:10] if published else None,
        doi=doi,
        arxiv_id=arxiv_id,
        source_url=abs_url,
        pdf_url=pdf_url,
        abstract=_clean_text(_text(entry, "atom:summary")),
        venue=_primary_category(entry),
        work_type="preprint",
        cited_by_count=0,
        is_open_access=True,
        source_api="arxiv",
        verified_by=["arxiv"],
        verification_status="candidate",
    )


def _text(entry: ET.Element, path: str) -> str:
    element = entry.find(path, ARXIV_NS)
    return element.text.strip() if element is not None and element.text else ""


def _authors(entry: ET.Element) -> list[str]:
    authors: list[str] = []
    for author in entry.findall("atom:author", ARXIV_NS):
        name = _text(author, "atom:name")
        if name:
            authors.append(_clean_text(name))
    return authors


def _pdf_url(entry: ET.Element) -> str | None:
    for link in entry.findall("atom:link", ARXIV_NS):
        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
            return link.attrib.get("href")
    return None


def _primary_category(entry: ET.Element) -> str | None:
    category = entry.find("arxiv:primary_category", ARXIV_NS)
    if category is not None:
        term = category.attrib.get("term")
        if term:
            return term
    return None


def _extract_arxiv_id(url: str) -> str | None:
    match = re.search(r"arxiv\.org/abs/([^v\s]+(?:v\d+)?)", url)
    if match:
        return match.group(1).strip()
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", url)
    return match.group(1) if match else None


def _year(value: str) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except ValueError:
        match = re.search(r"\b(19|20)\d{2}\b", value)
        return int(match.group(0)) if match else None


def _normalize_doi(raw: object) -> str | None:
    if not raw:
        return None
    doi = str(raw).strip()
    lower = doi.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lower.startswith(prefix):
            return doi[len(prefix):]
    return doi


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:48] or "unknown"


def _clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()
