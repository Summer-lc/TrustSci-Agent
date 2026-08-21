import asyncio
import json

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import CriticReview, Hypothesis

PERSPECTIVES = ("domain_scientist", "ml_critic", "skeptical_reviewer")

_PERSPECTIVE_PROMPTS = {
    "domain_scientist": "You are the Domain Scientist Critic. Score each hypothesis on scientific value, mechanism soundness, and domain novelty.",
    "ml_critic": "You are the ML/Experiment Critic. Score each hypothesis on data availability, feasibility, reproducibility, and verification path clarity.",
    "skeptical_reviewer": "You are the Skeptical Reviewer. Score each hypothesis on self-consistency, evidence support, and risk of overclaiming.",
}

_SYSTEM_TAIL = """

Score EVERY provided hypothesis on these 8 dimensions (integers 1..10): novelty, self_consistency, verifiability, data_availability, feasibility, evidence_support, reproducibility, competition_fit.
Return JSON only: {"reviews": [{"hypothesis_id": "...", "novelty": N, "self_consistency": N, "verifiability": N, "data_availability": N, "feasibility": N, "evidence_support": N, "reproducibility": N, "competition_fit": N, "risk": "...", "revision_advice": "..."}]}.
Do not invent citations or evidence ids."""


class CriticArenaAgent:
    """3-perspective parallel critic. Each perspective is an independent LCEL
    chain scoring all hypotheses on 8 dimensions. Runs concurrently via gather."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(self, hypotheses: list[Hypothesis], evidence: list[EvidenceItem], *, run_id: str) -> dict[str, dict[str, CriticReview]]:
        async def _one(perspective: str) -> dict[str, CriticReview]:
            return await self._run_perspective(perspective, hypotheses, evidence, run_id)
        results = await asyncio.gather(*[_one(p) for p in PERSPECTIVES])
        return dict(zip(PERSPECTIVES, results))

    async def _run_perspective(self, perspective: str, hypotheses: list[Hypothesis], evidence: list[EvidenceItem], run_id: str) -> dict[str, CriticReview]:
        fallback = {h.hypothesis_id: _fallback_review(h, perspective) for h in hypotheses}
        if self.llm is None:
            return fallback
        system = _PERSPECTIVE_PROMPTS[perspective] + _SYSTEM_TAIL
        prompt = build_agent_prompt(system)
        chain = (
            prompt
            | LLMClientRunnable(self.llm).bind(fallback={"reviews": []}, run_id=run_id, agent="critic_arena")
            | FallbackParser(lambda content: _normalize(content, hypotheses, fallback), fallback)
        )
        return await chain.ainvoke({"user_prompt": _build_user_prompt(hypotheses, evidence)})


def _build_user_prompt(hypotheses: list[Hypothesis], evidence: list[EvidenceItem]) -> str:
    payload = {
        "hypotheses": [{"hypothesis_id": h.hypothesis_id, "statement": h.statement, "rationale": h.rationale,
                         "verification_path": h.verification_path, "novelty_claim": h.novelty_claim,
                         "supporting_evidence": h.supporting_evidence} for h in hypotheses],
        "evidence": [{"evidence_id": e.evidence_id, "claim": e.claim, "verified": e.verified} for e in evidence[:16]],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize(content: object, hypotheses: list[Hypothesis], fallback: dict[str, CriticReview]) -> dict[str, CriticReview]:
    if not isinstance(content, dict) or not isinstance(content.get("reviews"), list):
        return fallback
    by_id = {str(r.get("hypothesis_id")): r for r in content["reviews"] if isinstance(r, dict) and r.get("hypothesis_id")}
    out: dict[str, CriticReview] = {}
    for h in hypotheses:
        raw = by_id.get(h.hypothesis_id)
        if not isinstance(raw, dict):
            out[h.hypothesis_id] = fallback[h.hypothesis_id]
            continue
        try:
            out[h.hypothesis_id] = CriticReview(
                novelty=_score(raw.get("novelty")), self_consistency=_score(raw.get("self_consistency")),
                verifiability=_score(raw.get("verifiability")), data_availability=_score(raw.get("data_availability")),
                feasibility=_score(raw.get("feasibility")), evidence_support=_score(raw.get("evidence_support")),
                reproducibility=_score(raw.get("reproducibility")), competition_fit=_score(raw.get("competition_fit")),
                risk=str(raw.get("risk") or "risk noted"), revision_advice=str(raw.get("revision_advice") or "revise bounds"),
            )
        except Exception:
            out[h.hypothesis_id] = fallback[h.hypothesis_id]
    # Ensure every hypothesis is covered; missing -> fallback.
    for h in hypotheses:
        out.setdefault(h.hypothesis_id, fallback[h.hypothesis_id])
    return out


def _fallback_review(hypothesis: Hypothesis, perspective: str) -> CriticReview:
    base = 8 if perspective != "skeptical_reviewer" else 6
    has_ev = 7 if hypothesis.supporting_evidence else 5
    return CriticReview(novelty=base, self_consistency=base, verifiability=base, data_availability=base - 1,
                        feasibility=base, evidence_support=has_ev, reproducibility=base - 1, competition_fit=base - 1,
                        risk="Deterministic fallback: evidence or feasibility risk requires revision.",
                        revision_advice="Bound novelty and tie to a concrete dataset/baseline.")


def _score(value: object) -> int:
    try:
        return max(1, min(10, int(float(value))))
    except (TypeError, ValueError):
        return 7
