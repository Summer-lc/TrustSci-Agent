from app.schemas.evidence import EvidenceItem
from app.schemas.paper import Paper


def evidence_from_papers(papers: list[Paper], domain: str) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for idx, paper in enumerate(papers, start=1):
        abstract = paper.abstract.strip()
        claim = _claim_from_paper(paper, domain)
        summary = abstract[:700] if abstract else f"Metadata confirms this work exists: {paper.title}."
        items.append(
            EvidenceItem(
                evidence_id=f"ev_{idx:03d}",
                paper_id=paper.paper_id,
                claim=claim,
                source_title=paper.title,
                source_url=paper.source_url,
                doi=paper.doi,
                quote_or_summary=summary,
                confidence=0.82 if paper.verification_status == "verified" else 0.62,
                verified=paper.verification_status == "verified",
                tags=[domain, "literature"],
            )
        )
    return items


def _claim_from_paper(paper: Paper, domain: str) -> str:
    title = paper.title.lower()
    if "solid" in title and "electroly" in title:
        return "Solid-state electrolyte literature links structure, transport pathways, and stability constraints."
    if "catalyst" in title or "catalysis" in title:
        return "Catalysis literature connects adsorption energetics, structure features, and screening strategies."
    if domain == "energy_materials":
        return "Energy materials research contains reusable evidence for structure-property-performance hypotheses."
    return "The paper provides domain evidence that can support a verifiable research hypothesis."

