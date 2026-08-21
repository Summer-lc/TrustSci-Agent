import json

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.arena import AblationChallenge
from app.schemas.hypothesis import Hypothesis
from app.schemas.idea import IdeaBrief

SYSTEM_PROMPT = """You are the Challenger Agent for TrustSci-Agent v3 (Idea Refinement ablation arena).
Given the user's main hypothesis (H_main) and idea brief, generate exactly 3 ablation challengers.
Each challenger removes or replaces ONE innovation point of H_main, to test whether that innovation point truly contributes.
Return JSON only: {"challenges": [{"challenge_id": "H_c1", "hypothesis_id": "H_c1", "statement": "...", "rationale": "...", "novelty_claim": "...", "verification_path": "...", "tests_innovation_point": "...", "expected_insight": "...", "derivation_from_main": "..."}]}.
Do not invent citations or datasets."""


class ChallengerAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(self, h_main: Hypothesis, idea_brief: IdeaBrief, *, run_id: str) -> tuple[list[Hypothesis], list[AblationChallenge]]:
        fallback = _fallback_challenges(h_main, idea_brief)
        if self.llm is None:
            return _split(fallback)
        chain = (
            build_agent_prompt(SYSTEM_PROMPT)
            | LLMClientRunnable(self.llm).bind(fallback={"challenges": []}, run_id=run_id, agent="challenger")
            | FallbackParser(lambda content: _normalize(content, h_main, fallback), fallback)
        )
        normalized = await chain.ainvoke({"user_prompt": _build_user_prompt(h_main, idea_brief)})
        return _split(normalized)


def _build_user_prompt(h_main: Hypothesis, idea_brief: IdeaBrief) -> str:
    payload = {
        "h_main": {"hypothesis_id": h_main.hypothesis_id, "statement": h_main.statement,
                   "rationale": h_main.rationale, "verification_path": h_main.verification_path,
                   "novelty_claim": h_main.novelty_claim},
        "idea_brief": {"user_idea": idea_brief.user_idea, "target_task": idea_brief.target_task,
                       "input_data": idea_brief.input_data, "target_labels": idea_brief.target_labels},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize(content: object, h_main: Hypothesis, fallback: list[dict]) -> list[dict]:
    if not isinstance(content, dict) or not isinstance(content.get("challenges"), list):
        return fallback
    out: list[dict] = []
    for raw in content["challenges"][:3]:
        if not isinstance(raw, dict):
            continue
        cid = str(raw.get("challenge_id") or raw.get("hypothesis_id") or "").strip()
        statement = str(raw.get("statement") or "").strip()
        if not cid or not statement:
            continue
        out.append({
            "challenge_id": cid, "hypothesis_id": cid, "statement": statement,
            "rationale": str(raw.get("rationale") or "ablation of an innovation point"),
            "novelty_claim": str(raw.get("novelty_claim") or "reduced variant"),
            "verification_path": str(raw.get("verification_path") or "compare against H_main"),
            "tests_innovation_point": str(raw.get("tests_innovation_point") or "an innovation point"),
            "expected_insight": str(raw.get("expected_insight") or "whether the innovation point contributes"),
            "derivation_from_main": str(raw.get("derivation_from_main") or "remove/replace an innovation point"),
        })
    return out or fallback


def _fallback_challenges(h_main: Hypothesis, idea_brief: IdeaBrief) -> list[dict]:
    inputs = idea_brief.input_data or ["waveform", "spectrogram"]
    variants = [
        ("H_c1", f"{h_main.statement} (waveform-only ablation)", "waveform branch",
         "whether waveform channel contributes", "remove non-waveform inputs"),
        ("H_c2", f"{h_main.statement} (single-representation ablation)", "multi-representation fusion",
         "whether fusion beats single representation", f"keep only {inputs[0] if inputs else 'one input'}"),
        ("H_c3", f"{h_main.statement} (simple-concat ablation)", "fusion module",
         "whether the fusion module beats simple concat", "replace fusion module with concatenation"),
    ]
    return [{
        "challenge_id": cid, "hypothesis_id": cid, "statement": stmt,
        "rationale": "ablation challenger to test an innovation point of H_main",
        "novelty_claim": "reduced variant of H_main", "verification_path": "compare against H_main",
        "tests_innovation_point": tip, "expected_insight": ei, "derivation_from_main": deriv,
    } for cid, stmt, tip, ei, deriv in variants]


def _split(challenges: list[dict]) -> tuple[list[Hypothesis], list[AblationChallenge]]:
    hyps = [Hypothesis(hypothesis_id=c["hypothesis_id"], statement=c["statement"], rationale=c["rationale"],
                       novelty_claim=c["novelty_claim"], verification_path=c["verification_path"]) for c in challenges]
    design = [AblationChallenge(challenge_id=c["challenge_id"], tests_innovation_point=c["tests_innovation_point"],
                                expected_insight=c["expected_insight"], derivation_from_main=c["derivation_from_main"]) for c in challenges]
    return hyps, design
