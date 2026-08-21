import json
from typing import Any

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.data import DatasetProfile
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import Hypothesis


SYSTEM_PROMPT = """You are the Hypothesis Generator Agent for TrustSci-Agent.
Generate exactly three candidate scientific hypotheses grounded in the supplied gaps, evidence, and data profiles.
Return JSON only. Do not claim a discovery has already been made. Do not invent citations, evidence ids, datasets, or completed results.

Required JSON shape:
{
  "hypotheses": [
    {
      "hypothesis_id": "H1",
      "statement": "testable hypothesis",
      "rationale": "why the supplied evidence makes this plausible",
      "supporting_evidence_ids": ["existing evidence ids only"],
      "novelty_boundary": "how it differs from supplied prior work",
      "verification_path": "falsifiable validation route",
      "required_dataset": "existing profile name or to be collected",
      "expected_contribution": "bounded expected contribution",
      "risk": "main risk",
      "evidence_sufficiency_note": "supported by evidence ids or evidence insufficient"
    }
  ]
}
Each hypothesis must be verifiable and must either include supporting_evidence_ids or explicitly say evidence insufficient.
"""

PROMPT = build_agent_prompt(SYSTEM_PROMPT)


class HypothesisAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(
        self,
        gaps: list[dict],
        evidence: list[EvidenceItem],
        data_profiles: list[DatasetProfile],
        *,
        run_id: str | None = None,
        avoid_prior_art: list[str] | None = None,
    ) -> list[Hypothesis]:
        fallback_hypotheses = self.run(gaps)
        if self.llm is None:
            return fallback_hypotheses
        fallback = {"hypotheses": [hypothesis.model_dump() for hypothesis in fallback_hypotheses]}
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback, run_id=run_id, agent="hypothesis_generator")
            | FallbackParser(
                lambda content: _normalize_hypotheses(content, fallback_hypotheses, evidence),
                fallback_hypotheses,
            )
        )
        return await chain.ainvoke({"user_prompt": _build_user_prompt(gaps, evidence, data_profiles, avoid_prior_art=avoid_prior_art)})

    def run(self, gaps: list[dict]) -> list[Hypothesis]:
        evidence_ids = gaps[0].get("evidence", []) if gaps else []
        return [
            Hypothesis(
                hypothesis_id="H1",
                statement="Combining literature-derived mechanism features with structure-property descriptors can improve prioritization of solid-state electrolyte candidates under stability constraints.",
                rationale="The hypothesis joins two evidence streams: verified papers describing transport/stability mechanisms and open datasets that support measurable property prediction.",
                supporting_evidence=evidence_ids,
                novelty_claim="The novelty is not a new material claim, but a traceable hypothesis workflow that connects mechanism text, database features, and explicit validation metrics.",
                verification_path="Build composition-only and structure-aware baselines, add literature-derived mechanism tags, and compare ranking and regression metrics.",
            ),
            Hypothesis(
                hypothesis_id="H2",
                statement="A citation-verified evidence ledger can reduce unsupported assumptions in early-stage energy-materials ideation while preserving enough diversity for expert review.",
                rationale="Current deep research systems often optimize answer synthesis; competition requirements demand stricter provenance for every key claim.",
                supporting_evidence=evidence_ids,
                novelty_claim="The claim focuses on trustworthy AI Scientist process design rather than unbounded autonomous discovery.",
                verification_path="Compare reports generated with and without citation freezing, then audit unsupported claims and rejected references.",
            ),
            Hypothesis(
                hypothesis_id="H3",
                statement="Human-in-the-loop critic scoring can select more verifiable hypotheses than single-pass generation for materials discovery questions.",
                rationale="Multi-agent debate exposes risks around novelty overlap, data availability, and metric mismatch before the final report is written.",
                supporting_evidence=evidence_ids,
                novelty_claim="The process explicitly optimizes for contest evaluation dimensions: novelty, self-consistency, verifiability, and reproducibility.",
                verification_path="Score candidate hypotheses before and after critic revision, then track accepted revisions and evidence coverage.",
            ),
        ]


def _build_user_prompt(
    gaps: list[dict],
    evidence: list[EvidenceItem],
    data_profiles: list[DatasetProfile],
    *,
    avoid_prior_art: list[str] | None = None,
) -> str:
    payload = {
        "gaps": gaps[:6],
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
            "Generate three distinct, testable hypotheses.",
            "Use only input evidence ids.",
            "Bound novelty and expected contribution; do not state unvalidated discoveries as facts.",
        ],
    }
    if avoid_prior_art:
        payload["instructions"].append(
            f"Avoid these already-done prior-art directions: {avoid_prior_art}. "
            "Generate a hypothesis in a different direction."
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_hypotheses(
    content: object,
    fallback: list[Hypothesis],
    evidence: list[EvidenceItem],
) -> list[Hypothesis]:
    if not isinstance(content, dict) or not isinstance(content.get("hypotheses"), list):
        return fallback
    allowed_evidence = {item.evidence_id for item in evidence}
    hypotheses: list[Hypothesis] = []
    for index, raw in enumerate(content["hypotheses"][:3], start=1):
        if not isinstance(raw, dict):
            continue
        evidence_ids = _known_ids(raw.get("supporting_evidence_ids") or raw.get("supporting_evidence"), allowed_evidence)
        sufficiency = _clean(raw.get("evidence_sufficiency_note"))
        if not evidence_ids and "evidence insufficient" not in sufficiency.lower():
            sufficiency = f"{sufficiency}; evidence insufficient".strip("; ")
        statement = _clean(raw.get("statement"))
        rationale = _clean(raw.get("rationale"))
        verification_path = _clean(raw.get("verification_path"))
        novelty = _clean(raw.get("novelty_boundary") or raw.get("novelty_claim"))
        if not statement or not rationale or not verification_path or not novelty:
            continue
        risk = _clean(raw.get("risk")) or "Risk: evidence may be too sparse for strong claims."
        required_dataset = _clean(raw.get("required_dataset")) or "to be collected or selected from existing data profiles"
        contribution = _clean(raw.get("expected_contribution")) or "bounded, verification-pending contribution"
        hypotheses.append(
            Hypothesis(
                hypothesis_id=_clean(raw.get("hypothesis_id")) or f"H{index}",
                statement=statement,
                rationale=(
                    f"{rationale} Required dataset: {required_dataset}. "
                    f"Expected contribution: {contribution}. Risk: {risk}. "
                    f"Evidence sufficiency: {sufficiency or 'evidence insufficient'}"
                ),
                supporting_evidence=evidence_ids,
                novelty_claim=novelty,
                verification_path=verification_path,
            )
        )
    return hypotheses or fallback


def _known_ids(value: object, allowed: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in [str(raw).strip() for raw in value] if item in allowed]


def _clean(value: object) -> str:
    return str(value or "").strip()
