from app.schemas.paper import Paper


def build_citation_audit(papers: list[Paper]) -> list[str]:
    audit: list[str] = []
    for paper in papers:
        status = paper.verification_status
        doi = paper.doi or "no DOI"
        score = f", title_match={paper.title_match_score}" if paper.title_match_score is not None else ""
        sources = ",".join(paper.verified_by) or "none"
        audit.append(f"{paper.paper_id}: {status} via {sources}; DOI={doi}{score}; title={paper.title}")
    return audit

