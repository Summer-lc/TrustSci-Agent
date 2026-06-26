import re
import json

from app.llm.interface import LLMClient, LLMRequest
from app.schemas.claim import ClaimAuditItem, ClaimAuditReport
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import Hypothesis
from app.schemas.report import ResearchReport
from app.schemas.run import ResearchRun


SYSTEM_PROMPT = """You are the Claim Verifier Agent for TrustSci-Agent.
Audit report claims against the provided eligible evidence ledger.
Return JSON only. Do not invent evidence ids, citations, papers, datasets, or new claims.

Required JSON shape:
{
  "claim_audits": [
    {
      "claim_id": "claim_001",
      "status": "supported | weakly_supported | unsupported",
      "confidence": 0.0,
      "matched_evidence_ids": ["existing evidence ids only"],
      "reason": "brief sentence-level support judgement"
    }
  ]
}

Rules:
- Only judge the supplied claim_id values.
- supported means the evidence directly supports the specific sentence.
- weakly_supported means the evidence is relevant but incomplete, indirect, or too broad.
- unsupported means no eligible evidence supports the sentence, or the sentence describes unverified results.
- If a claim has no valid matched_evidence_ids, its status must be unsupported.
"""


class ClaimVerifier:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(
        self,
        run: ResearchRun,
        report: ResearchReport,
        evidence: list[EvidenceItem],
        hypothesis: Hypothesis | None,
    ) -> ClaimAuditReport:
        fallback = self.audit(run, report, evidence, hypothesis)
        if self.llm is None:
            return fallback
        response = await self.llm.complete(
            LLMRequest(
                system=SYSTEM_PROMPT,
                user=_build_user_prompt(fallback.items, evidence),
                fallback={"claim_audits": [item.model_dump() for item in fallback.items]},
                run_id=run.run_id,
                agent="claim_verifier",
            )
        )
        return _normalize_qwen_audit(response.content, fallback, evidence)

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
            artifact_reason = _artifact_support_reason(claim, run, report)
            if artifact_reason:
                matched = []
                score = 1.0
                status = "supported"
                reason = artifact_reason
            else:
                matched, score = _match_evidence(claim, eligible_evidence)
                status = _status(score, matched)
                reason = _reason(status, matched)
            items.append(
                ClaimAuditItem(
                    claim_id=f"claim_{index:03d}",
                    claim=claim,
                    status=status,
                    confidence=score,
                    matched_evidence_ids=[item.evidence_id for item in matched[:3]],
                    reason=reason,
                )
            )
        return _report(items)


def _candidate_claims(
    run: ResearchRun,
    report: ResearchReport,
    hypothesis: Hypothesis | None,
) -> list[str]:
    raw = [
        report.problem_statement,
        report.rationale,
        report.results,
    ]
    raw.extend(report.technical_details[:3])
    raw.extend(report.methods[:5])
    raw.extend(
        [
            report.source,
            report.target,
            report.experiments.expected_results,
            *report.experiments.experiment_steps[:4],
        ]
    )
    claims: list[str] = []
    for value in raw:
        if not value:
            continue
        for sentence in _claim_sentences(str(value)):
            if len(sentence) < 24:
                continue
            if _is_validation_statement(sentence):
                continue
            claims.append(sentence[:420])
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


def _artifact_support_reason(claim: str, run: ResearchRun, report: ResearchReport) -> str:
    text = claim.lower()
    has_steps = any(step.status == "completed" for step in run.steps)
    has_references = bool(report.references)
    has_evidence = bool(run.evidence)
    if ("baseline result card" in text or "metrics=" in text or "train_rows" in text) and report.baseline_result_card:
        return "Supported by the baseline result card artifact."
    if ("verified references" in text or "verified papers" in text or "report references" in text) and has_references:
        return "Supported by verified reference metadata in the run artifact."
    if "verified evidence" in text and has_evidence:
        return "Supported by the frozen evidence ledger artifact."
    if "plan the research question" in text and (run.plan or has_steps or report.experiments):
        return "Supported by completed workflow steps in the run artifact."
    if "profile " in text and "scientific datasets" in text:
        return "Supported by scientific data profile artifacts in the run."
    if ("retrieve candidate papers" in text or "literature router" in text) and run.papers:
        return "Supported by collected paper metadata and citation audit artifacts."
    if "citation audit" in text and report.citation_audit_log:
        return "Supported by the citation audit log artifact."
    return ""


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


def _build_user_prompt(items: list[ClaimAuditItem], evidence: list[EvidenceItem]) -> str:
    eligible_evidence = [item for item in evidence if item.eligible_for_report]
    payload = {
        "claims": [
            {
                "claim_id": item.claim_id,
                "claim": item.claim,
                "fallback_status": item.status,
                "fallback_matched_evidence_ids": item.matched_evidence_ids,
            }
            for item in items
        ],
        "eligible_evidence": [
            {
                "evidence_id": item.evidence_id,
                "paper_id": item.paper_id,
                "claim": item.claim,
                "quote_or_summary": item.quote_or_summary,
                "source_title": item.source_title,
                "verified": item.verified,
                "eligible_for_report": item.eligible_for_report,
            }
            for item in eligible_evidence[:24]
        ],
        "instructions": [
            "Judge each claim sentence against eligible evidence only.",
            "Use supported only for direct support.",
            "Use weakly_supported for relevant but partial support.",
            "Use unsupported for unverified result claims, missing evidence, or broad statements not tied to evidence.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_qwen_audit(
    content: object,
    fallback: ClaimAuditReport,
    evidence: list[EvidenceItem],
) -> ClaimAuditReport:
    if not isinstance(content, dict) or not isinstance(content.get("claim_audits"), list):
        return fallback
    fallback_by_id = {item.claim_id: item for item in fallback.items}
    evidence_ids = {
        item.evidence_id
        for item in evidence
        if item.eligible_for_report and item.verified
    }
    qwen_by_id = {
        str(raw.get("claim_id")): raw
        for raw in content["claim_audits"]
        if isinstance(raw, dict) and raw.get("claim_id")
    }
    items: list[ClaimAuditItem] = []
    for fallback_item in fallback.items:
        raw = qwen_by_id.get(fallback_item.claim_id)
        if raw is None:
            items.append(fallback_item)
            continue
        matched_ids = _known_ids(raw.get("matched_evidence_ids"), evidence_ids)
        status = _qwen_status(raw.get("status"))
        if not matched_ids:
            status = "unsupported"
        confidence = _confidence(raw.get("confidence"))
        if status == "unsupported":
            confidence = min(confidence, 0.09)
        elif status == "weakly_supported":
            confidence = min(max(confidence, 0.1), 0.69)
        else:
            confidence = max(confidence, 0.7)
        items.append(
            ClaimAuditItem(
                claim_id=fallback_item.claim_id,
                claim=fallback_item.claim,
                status=status,
                confidence=confidence,
                matched_evidence_ids=matched_ids,
                reason=_clean(str(raw.get("reason") or "")) or _reason(status, []),
            )
        )
    return _report(items)


def _claim_sentences(text: str) -> list[str]:
    text = _clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
    sentences = [_clean(part) for part in parts if _clean(part)]
    if not sentences:
        return [text]
    expanded: list[str] = []
    for sentence in sentences:
        if len(sentence) <= 420:
            expanded.append(sentence)
            continue
        clauses = re.split(r";\s+|；\s+|\.\s+", sentence)
        expanded.extend(_clean(clause) for clause in clauses if len(_clean(clause)) >= 24)
    return expanded or [text[:420]]


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    return {word for word in words if word not in _STOPWORDS}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _is_validation_statement(text: str) -> bool:
    lowered = text.lower().strip()
    return lowered.startswith("to validate:") or any(
        marker in lowered
        for marker in [
            "verification pending",
            "requires validation",
            "require validation",
            "will test",
            "we propose",
            "proposed experiment",
            "planned validation",
            "not a completed discovery",
            "not as an already-proven",
        ]
    )


def _known_ids(value: object, allowed: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in [str(raw).strip() for raw in value] if item in allowed]


def _qwen_status(value: object) -> str:
    status = str(value or "").strip().lower()
    if status in {"supported", "weakly_supported", "unsupported"}:
        return status
    return "unsupported"


def _confidence(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


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
