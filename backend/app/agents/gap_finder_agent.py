import json
from typing import Any

from app.llm.interface import LLMClient, LLMRequest
from app.schemas.data import DatasetProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.knowledge import KnowledgeCard


SYSTEM_PROMPT = """You are the Gap Finder Agent for TrustSci-Agent.
Find research gaps grounded in the provided knowledge cards, evidence, and dataset profiles.
Return JSON only. Do not invent citations, evidence ids, datasets, or solved results.

Required JSON shape:
{
  "gaps": [
    {
      "gap_id": "gap_001",
      "unresolved_gap": "specific gap statement",
      "what_literature_shows": "what the supplied evidence supports",
      "what_is_not_solved": "what remains unresolved",
      "why_worth_exploring": "scientific value",
      "verification_opportunity": "how to test it",
      "underexplored_method_combination": "method combination, or evidence insufficient",
      "data_availability_opportunity": "data opportunity, or evidence insufficient",
      "risk_uncertainty": "risk or evidence insufficient",
      "supporting_evidence_ids": ["existing evidence ids only"]
    }
  ]
}
Every gap must either cite supporting_evidence_ids from input or explicitly say evidence insufficient.
"""


class GapFinderAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(
        self,
        knowledge_cards: list[KnowledgeCard],
        evidence: list[EvidenceItem],
        data_profiles: list[DatasetProfile],
        *,
        run_id: str | None = None,
    ) -> list[dict]:
        fallback_gaps = self.run(evidence)
        if self.llm is None:
            return fallback_gaps
        fallback = {"gaps": fallback_gaps}
        response = await self.llm.complete(
            LLMRequest(
                system=SYSTEM_PROMPT,
                user=_build_user_prompt(knowledge_cards, evidence, data_profiles),
                fallback=fallback,
                run_id=run_id,
                agent="gap_finder",
            )
        )
        return _normalize_gaps(response.content, fallback_gaps, evidence)

    def run(self, evidence: list[EvidenceItem]) -> list[dict]:
        verified = [item for item in evidence if item.verified]
        anchors = verified[:3] or evidence[:3]
        ids = [item.evidence_id for item in anchors]
        return [
            {
                "gap_id": "gap_001",
                "gap": "Existing studies are often split between literature-level mechanism descriptions and structured dataset modeling; the bridge between mechanistic text evidence and quantitative verification remains underdeveloped.",
                "evidence": ids,
                "potential_value": "A literature-augmented validation plan can improve hypothesis traceability and make screening decisions easier to audit.",
            }
        ]


def _build_user_prompt(
    knowledge_cards: list[KnowledgeCard],
    evidence: list[EvidenceItem],
    data_profiles: list[DatasetProfile],
) -> str:
    payload = {
        "knowledge_cards": [
            {
                "card_id": card.card_id,
                "title": card.title,
                "perspective": card.perspective,
                "finding": card.finding,
                "method": card.method,
                "dataset": card.dataset,
                "limitation": card.limitation,
                "transferability": card.transferability,
                "evidence_ids": card.evidence_ids,
                "paper_ids": card.paper_ids,
            }
            for card in knowledge_cards[:12]
        ],
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "paper_id": item.paper_id,
                "claim": item.claim,
                "quote_or_summary": item.quote_or_summary,
                "verified": item.verified,
                "eligible_for_report": item.eligible_for_report,
            }
            for item in evidence[:16]
        ],
        "data_profiles": [
            {
                "name": profile.name,
                "source": profile.source,
                "rows": profile.rows,
                "target": profile.target,
                "task_type": profile.task_type,
                "availability": profile.availability,
            }
            for profile in data_profiles
        ],
        "instructions": [
            "Explain what existing literature shows, what remains unsolved, why it matters, evidence support, and verification route.",
            "Write evidence insufficient when support is weak.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_gaps(content: object, fallback: list[dict], evidence: list[EvidenceItem]) -> list[dict]:
    if not isinstance(content, dict) or not isinstance(content.get("gaps"), list):
        return fallback
    allowed_evidence = {item.evidence_id for item in evidence}
    gaps: list[dict] = []
    for index, raw in enumerate(content["gaps"][:5], start=1):
        if not isinstance(raw, dict):
            continue
        evidence_ids = _known_ids(raw.get("supporting_evidence_ids") or raw.get("evidence"), allowed_evidence)
        risk = _clean(raw.get("risk_uncertainty"))
        if not evidence_ids and "evidence insufficient" not in risk.lower():
            risk = f"{risk}; evidence insufficient".strip("; ")
        gap_statement = _clean(raw.get("unresolved_gap") or raw.get("gap"))
        what_is_not_solved = _clean(raw.get("what_is_not_solved"))
        why = _clean(raw.get("why_worth_exploring") or raw.get("potential_value"))
        verification = _clean(raw.get("verification_opportunity"))
        if not gap_statement or not why:
            continue
        gaps.append(
            {
                "gap_id": _clean(raw.get("gap_id")) or f"gap_{index:03d}",
                "gap": gap_statement,
                "what_literature_shows": _clean(raw.get("what_literature_shows")),
                "what_is_not_solved": what_is_not_solved or "evidence insufficient",
                "why_worth_exploring": why,
                "verification_opportunity": verification or "Define a bounded validation task before claiming resolution.",
                "underexplored_method_combination": _clean(raw.get("underexplored_method_combination")),
                "data_availability_opportunity": _clean(raw.get("data_availability_opportunity")),
                "risk_uncertainty": risk or "evidence insufficient",
                "evidence": evidence_ids,
                "supporting_evidence_ids": evidence_ids,
                "potential_value": why,
            }
        )
    return gaps or fallback


def _known_ids(value: object, allowed: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in [str(raw).strip() for raw in value] if item in allowed]


def _clean(value: object) -> str:
    return str(value or "").strip()
