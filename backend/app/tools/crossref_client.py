import httpx
from rapidfuzz import fuzz

from app.schemas.paper import Paper


class CrossrefClient:
    async def verify(self, paper: Paper) -> Paper:
        if not paper.doi:
            paper.verification_status = "suspicious"
            return paper

        url = f"https://api.crossref.org/works/{paper.doi}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url)
                response.raise_for_status()
            message = response.json().get("message", {})
        except Exception:
            paper.verification_status = "suspicious"
            return paper

        titles = message.get("title") or []
        canonical_title = titles[0] if titles else ""
        score = fuzz.token_set_ratio(paper.title, canonical_title) / 100 if canonical_title else 0
        paper.title_match_score = round(score, 3)
        if "crossref" not in paper.verified_by:
            paper.verified_by.append("crossref")
        paper.verification_status = "verified" if score >= 0.82 else "suspicious"
        return paper

