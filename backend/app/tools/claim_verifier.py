import re

from app.schemas.claim import ClaimAuditItem, ClaimAuditReport
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import Hypothesis
from app.schemas.report import ResearchReport
from app.schemas.run import ResearchRun


class ClaimVerifier:
    def audit(
        self,
        run: ResearchRun,
        report: ResearchReport,
        evidence: list[EvidenceItem],
        hypothesis: Hypothesis | None,
    ) -> ClaimAuditReport:
        claims = _candidate_claims(run, report, hypothesis)
        eligible_evidence = [item for item in evidence if item.eligible_for_report]
        items: list[ClaimAuditItem] = []
        for index, claim in enumerate(claims, start=1):
            matched, score = _match_evidence(claim, eligible_evidence)
            status = _status(score, matched)
            items.append(
                ClaimAuditItem(
                    claim_id=f"claim_{index:03d}",
                    claim=claim,
                    status=status,
                    confidence=score,
                    matched_evidence_ids=[item.evidence_id for item in matched[:3]],
                    reason=_reason(status, matched),
                )
            )
        return _report(items)


def _candidate_claims(
    run: ResearchRun,
    report: ResearchReport,
    hypothesis: Hypothesis | None,
) -> list[str]:
    raw = [
        run.question,
        hypothesis.revised_statement if hypothesis and hypothesis.revised_statement else None,
        hypothesis.statement if hypothesis else None,
        report.problem_statement,
        report.rationale,
        report.results,
    ]
    raw.extend(report.methods[:4])
    claims: list[str] = []
    for value in raw:
        if not value:
            continue
        text = _clean(str(value))
        if len(text) < 24:
            continue
        claims.append(text[:420])
    return _dedupe(claims)[:10]


def _match_evidence(claim: str, evidence: list[EvidenceItem]) -> tuple[list[EvidenceItem], float]:
    claim_terms = _terms(claim)
    if not claim_terms or not evidence:
        return [], 0.0

    scored: list[tuple[float, EvidenceItem]] = []
    for item in evidence:
        evidence_terms = _terms(" ".join([item.claim, item.quote_or_summary, item.source_title]))
        if not evidence_terms:
            continue
        overlap = len(claim_terms & evidence_terms) / max(len(claim_terms), 1)
        weighted = overlap * (1.0 if item.verified else 0.65)
        if weighted > 0:
            scored.append((round(weighted, 3), item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    best_score = scored[0][0] if scored else 0.0
    matches = [item for score, item in scored if score >= max(0.12, best_score * 0.7)]
    return matches, best_score


def _status(score: float, matched: list[EvidenceItem]) -> str:
    if matched and score >= 0.22:
        return "supported"
    if matched and score >= 0.10:
        return "weakly_supported"
    return "unsupported"


def _reason(status: str, matched: list[EvidenceItem]) -> str:
    if status == "supported":
        return "Matched eligible evidence from the frozen evidence ledger."
    if status == "weakly_supported":
        return "Matched eligible evidence, but lexical support is weak and should be reviewed."
    return "No eligible evidence item matched this claim."


def _report(items: list[ClaimAuditItem]) -> ClaimAuditReport:
    total = len(items)
    supported = len([item for item in items if item.status == "supported"])
    weak = len([item for item in items if item.status == "weakly_supported"])
    unsupported = len([item for item in items if item.status == "unsupported"])
    support_score = round((supported + 0.5 * weak) / total, 3) if total else 1.0
    return ClaimAuditReport(
        total=total,
        supported=supported,
        weakly_supported=weak,
        unsupported=unsupported,
        support_score=support_score,
        items=items,
    )


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    return {word for word in words if word not in _STOPWORDS}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(value)
    return deduped


_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "while",
    "before",
    "after",
    "current",
    "report",
    "research",
    "evidence",
    "verified",
    "verification",
    "candidate",
    "system",
    "agent",
    "plan",
}
