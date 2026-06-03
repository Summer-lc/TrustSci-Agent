from app.schemas.paper import Paper


def build_citation_audit(papers: list[Paper]) -> list[str]:
    audit: list[str] = []
    for paper in papers:
        status = paper.verification_status
        doi = paper.doi or "no DOI"
        score = f", title_match={paper.title_match_score}" if paper.title_match_score is not None else ""
        sources = ",".join(paper.verified_by) or "none"
        method = paper.verification_method or "unknown"
        confidence = (
            f", confidence={paper.verification_confidence}"
            if paper.verification_confidence is not None
            else ""
        )
        matched = f"; matched={paper.matched_source}" if paper.matched_source else ""
        eligibility = "eligible" if paper.report_eligible else "audit_only"
        audit.append(
            f"{paper.paper_id}: {status}/{eligibility} via {method} ({sources}); "
            f"DOI={doi}{score}{confidence}{matched}; title={paper.title}"
        )
    return audit
