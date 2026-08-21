from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable
from app.schemas.idea import IdeaBrief
from app.schemas.run import ResearchRun

SYSTEM_PROMPT = """You are the Idea Intake Agent for TrustSci-Agent v3 (Idea Refinement mode).
Structure the user's concrete research idea into an IdeaBrief.
Return JSON only with keys:
- research_problem: str
- user_idea: str (the user's proposed method, verbatim in spirit)
- target_task: str
- input_data: list[str]
- proposed_method: str | null
- expected_contribution: str | null
- target_labels: list[str]
- unknowns: list[str]
- risks: list[str]
Do not invent citations, datasets, or results. Mark uncertain items in unknowns/risks."""

USER_TEMPLATE = """Domain: {domain}
Question: {question}

Structure the user's idea into an IdeaBrief JSON."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)])


class IdeaBriefParser(Runnable):
    def __init__(self, fallback: IdeaBrief) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> IdeaBrief:
        try:
            return _normalize(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> IdeaBrief:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> IdeaBrief:
        return self.parse(input)


class IdeaIntakeAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, run: ResearchRun) -> IdeaBrief:
        fallback = _fallback_brief(run)
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback.model_dump(), run_id=run.run_id, agent="idea_intake")
            | IdeaBriefParser(fallback=fallback)
        )
        return await chain.ainvoke({"domain": run.domain, "question": run.question})


def _normalize(content: object, fallback: IdeaBrief) -> IdeaBrief:
    if not isinstance(content, dict):
        return fallback
    payload = fallback.model_dump()
    payload.update(content)
    return IdeaBrief.model_validate(payload)


def _fallback_brief(run: ResearchRun) -> IdeaBrief:
    return IdeaBrief(
        research_problem=run.question,
        user_idea=run.question,
        target_task="earthquake/explosion/noise classification" if "seismic" in run.domain else run.question,
        input_data=["three-component waveform", "spectrogram"] if "seismic" in run.domain else [],
        target_labels=["earthquake", "explosion", "noise"] if "seismic" in run.domain else [],
        unknowns=["公开数据是否包含目标标签", "是否有相似已发表方法", "baseline 代码是否可复现"],
        risks=["创意创新点可能与已有工作重合", "公开数据标签不足"],
    )
