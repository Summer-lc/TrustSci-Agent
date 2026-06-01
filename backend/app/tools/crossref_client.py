import html
import re
from typing import Any
from urllib.parse import quote

import httpx
from rapidfuzz import fuzz

from app.config import Settings
from app.schemas.paper import Paper


_CROSSREF_WORKS_URL = "https://api.crossref.org/works"
_TITLE_VERIFY_THRESHOLD = 0.82


class CrossrefClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    async def verify(self, paper: Paper) -> Paper:
        if not paper.doi:
            paper.verification_status = "suspicious"
            return paper

        try:
            async with httpx.AsyncClient(timeout=20, transport=self.transport) as client:
                response = await client.get(
                    f"{_CROSSREF_WORKS_URL}/{quote(paper.doi, safe='/')}",
                    params=self._params(),
                    headers=self._headers(),
                )
                response.raise_for_status()
            message = response.json().get("message", {})
        except Exception:
            paper.verification_status = "suspicious"
            return paper

        self._apply_metadata(paper, message)
        canonical_title = _first(message.get("title"))
        score = fuzz.token_set_ratio(paper.title, canonical_title) / 100 if canonical_title else 0
        paper.title_match_score = round(score, 3)
        if "crossref" not in paper.verified_by:
            paper.verified_by.append("crossref")
        year_ok = _year_matches(paper.year, _published_year(message))
        paper.verification_status = "verified" if score >= _TITLE_VERIFY_THRESHOLD and year_ok else "suspicious"
        return paper

    def _params(self) -> dict[str, str]:
        email = self.settings.crossref_email or self.settings.openalex_email
        return {"mailto": email} if email else {}

    def _headers(self) -> dict[str, str]:
        email = self.settings.crossref_email or self.settings.openalex_email
        contact = f" (mailto:{email})" if email else ""
        return {"User-Agent": f"TrustSci-Agent/0.1{contact}"}

    @staticmethod
    def _apply_metadata(paper: Paper, message: dict[str, Any]) -> None:
        paper.doi = _normalize_doi(message.get("DOI")) or paper.doi
        paper.title = paper.title or _first(message.get("title")) or "Untitled"
        if not paper.authors:
            paper.authors = _authors(message.get("author"))
        paper.year = paper.year or _published_year(message)
        paper.publication_date = paper.publication_date or _published_date(message)
        paper.venue = paper.venue or _first(message.get("container-title"))
        paper.work_type = paper.work_type or message.get("type")
        paper.cited_by_count = paper.cited_by_count if paper.cited_by_count is not None else message.get("is-referenced-by-count")
        if paper.source_url is None and paper.doi:
            paper.source_url = f"https://doi.org/{paper.doi}"
        paper.source_api = paper.source_api if paper.source_api != "unknown" else "crossref"


def _first(value: object) -> str:
    if isinstance(value, list) and value:
        return _clean_text(value[0])
    if isinstance(value, str):
        return _clean_text(value)
    return ""


def _authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        full = item.get("name")
        if full:
            names.append(_clean_text(full))
            continue
        given = str(item.get("given") or "").strip()
        family = str(item.get("family") or "").strip()
        name = " ".join(part for part in [given, family] if part)
        if name:
            names.append(name)
    return names


def _published_year(message: dict[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "published", "issued"):
        date_parts = ((message.get(key) or {}).get("date-parts") or [])
        if date_parts and date_parts[0]:
            try:
                return int(date_parts[0][0])
            except (TypeError, ValueError):
                return None
    return None


def _published_date(message: dict[str, Any]) -> str | None:
    for key in ("published-print", "published-online", "published", "issued"):
        date_parts = ((message.get(key) or {}).get("date-parts") or [])
        if date_parts and date_parts[0]:
            parts = [str(part) for part in date_parts[0]]
            if len(parts) == 1:
                return parts[0]
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1].zfill(2)}"
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
    return None


def _year_matches(paper_year: int | None, crossref_year: int | None) -> bool:
    if paper_year is None or crossref_year is None:
        return True
    return abs(paper_year - crossref_year) <= 1


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
