import pytest

from app.agents.idea_intake_agent import IdeaIntakeAgent, SYSTEM_PROMPT
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.run import ResearchConstraints, ResearchRun


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


@pytest.mark.asyncio
async def test_idea_intake_returns_brief() -> None:
    llm = FakeLLM({
        "research_problem": "地震事件分类",
        "user_idea": "多通道波形与时频图融合",
        "target_task": "earthquake/explosion/noise classification",
        "input_data": ["three-component waveform", "spectrogram"],
        "target_labels": ["earthquake", "explosion", "noise"],
        "unknowns": ["公开数据是否包含目标标签"],
    })
    agent = IdeaIntakeAgent(llm)
    run = ResearchRun(domain="seismic_event_classification", question="我想用多通道波形+时频图融合区分地震和爆破", constraints=ResearchConstraints())
    brief = await agent.run(run)
    assert brief.user_idea == "多通道波形与时频图融合"
    assert brief.target_labels == ["earthquake", "explosion", "noise"]
    assert llm.requests[0].agent == "idea_intake"
    assert llm.requests[0].system == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_idea_intake_falls_back_on_bad_output() -> None:
    for bad in ("nope", None, [1], 7, {"user_idea": "x"}):
        agent = IdeaIntakeAgent(FakeLLM(bad))
        run = ResearchRun(domain="seismic_event_classification", question="我想用一个新融合方法", constraints=ResearchConstraints())
        brief = await agent.run(run)
        assert brief.research_problem
        assert brief.target_task
        assert brief.user_idea is not None
