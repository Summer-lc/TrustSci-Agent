from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable
from app.schemas.mode import ResearchMode
from app.schemas.run import ResearchRun

SYSTEM_PROMPT = """You are the Intent Router Agent for TrustSci-Agent v3.
Classify the user's research input into exactly one of three entry modes.

Modes:
- discovery: the user only has a fuzzy research direction and no concrete method or code.
- idea_refinement: the user already proposes a concrete method/idea to be validated.
- experiment_assistance: the user already has data, code, or results and wants baselines/ablations/reporting filled in.

Return JSON only with keys:
- mode: one of "discovery", "idea_refinement", "experiment_assistance"
- confidence: float in [0,1]
- reason: one sentence why this mode fits
- required_inputs: list of input kinds the downstream workflow needs (e.g. ["question"], ["question","idea"], ["question","data_path","code_path"])
"""

USER_TEMPLATE = """Domain: {domain}
Question: {question}
Mode hint from UI: {mode_hint}

Classify the research entry mode. Do not invent references or results."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)])

_VALID_MODES = {"discovery", "idea_refinement", "experiment_assistance"}


class IntentRouterResultParser(Runnable):
    def __init__(self, fallback: dict) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> dict:
        try:
            return _normalize(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)


class IntentRouterAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, run: ResearchRun) -> dict:
        fallback = _fallback_intent(run)
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback, run_id=run.run_id, agent="intent_router")
            | IntentRouterResultParser(fallback=fallback)
        )
        return await chain.ainvoke(_prompt_vars(run))


def _prompt_vars(run: ResearchRun) -> dict:
    return {"domain": run.domain, "question": run.question, "mode_hint": run.mode}


def _normalize(content: object, fallback: dict) -> dict:
    if not isinstance(content, dict):
        return fallback
    mode = str(content.get("mode", "")).strip()
    if mode not in _VALID_MODES:
        return fallback
    required = content.get("required_inputs", fallback["required_inputs"])
    if not isinstance(required, list):
        required = fallback["required_inputs"]
    return {
        "mode": mode,
        "confidence": _float(content.get("confidence", fallback["confidence"])),
        "reason": str(content.get("reason", fallback["reason"])).strip() or fallback["reason"],
        "required_inputs": [str(x) for x in required if str(x).strip()],
    }


def _float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _fallback_intent(run: ResearchRun) -> dict:
    q = run.question.lower()
    exp_keywords = ["已有代码", "已有数据", "已有结果", "已有实验", "already have", "existing code", "existing model", "补 baseline", "补消融"]
    idea_keywords = ["创意", "想法", "我想用", "我想提出", "my idea", "i propose", "propose"]
    if any(k in q for k in exp_keywords):
        mode: ResearchMode = "experiment_assistance"
        required = ["question", "data_path", "code_path"]
        reason = "User mentions existing code/data/results; treat as experiment assistance."
    elif any(k in q for k in idea_keywords):
        mode = "idea_refinement"
        required = ["question", "idea"]
        reason = "User proposes a concrete method; refine the idea."
    else:
        mode = "discovery"
        required = ["question"]
        reason = "Only a research direction is given; discover hypotheses from scratch."
    return {"mode": mode, "confidence": 0.5, "reason": reason, "required_inputs": required}
