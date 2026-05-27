from app.evidence.audit import build_citation_audit
from app.schemas.paper import Paper


def test_citation_audit_includes_verification_status() -> None:
    paper = Paper(
        paper_id="paper_001",
        title="A test paper",
        doi="10.0000/example",
        verification_status="verified",
        verified_by=["openalex", "crossref"],
        title_match_score=0.93,
    )

    audit = build_citation_audit([paper])

    assert "verified" in audit[0]
    assert "10.0000/example" in audit[0]
    assert "title_match=0.93" in audit[0]

