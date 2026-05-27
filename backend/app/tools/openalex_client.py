from urllib.parse import quote

import httpx

from app.config import Settings
from app.schemas.paper import Paper


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in index.items():
        for position in indexes:
            positions.append((position, word))
    return " ".join(word for _, word in sorted(positions))


class OpenAlexClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def search(self, query: str, limit: int) -> list[Paper]:
        params = f"search={quote(query)}&per-page={limit}"
        if self.settings.openalex_email:
            params += f"&mailto={quote(self.settings.openalex_email)}"
        url = f"https://api.openalex.org/works?{params}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
        results = response.json().get("results", [])

        papers: list[Paper] = []
        for idx, item in enumerate(results, start=1):
            authors = [
                authorship.get("author", {}).get("display_name", "")
                for authorship in item.get("authorships", [])
            ]
            ids = item.get("ids", {}) or {}
            doi = ids.get("doi")
            if doi and doi.startswith("https://doi.org/"):
                doi = doi.replace("https://doi.org/", "")
            papers.append(
                Paper(
                    paper_id=f"paper_{idx:03d}",
                    title=item.get("display_name") or "Untitled",
                    authors=[name for name in authors if name],
                    year=item.get("publication_year"),
                    doi=doi,
                    source_url=item.get("primary_location", {}).get("landing_page_url") or ids.get("openalex"),
                    abstract=_abstract_from_inverted_index(item.get("abstract_inverted_index")),
                    venue=(item.get("primary_location", {}).get("source") or {}).get("display_name"),
                    verified_by=["openalex"],
                    verification_status="candidate",
                )
            )
        return papers

