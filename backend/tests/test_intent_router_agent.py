import pytest

from app.agents.intent_router_agent import IntentRouterAgent, SYSTEM_PROMPT
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
async def test_intent_router_returns_llm_mode() -> None:
    llm = FakeLLM({"mode": "idea_refinement", "confidence": 0.9, "reason": "user proposes a method", "required_inputs": ["question", "idea"]})
    agent = IntentRouterAgent(llm)
    run = ResearchRun(domain="seismic_event_classification", question="我想用多通道波形+时频图融合区分地震和爆破", constraints=ResearchConstraints())
    result = await agent.run(run)
    assert result["mode"] == "idea_refinement"
    assert result["required_inputs"] == ["question", "idea"]
    assert llm.requests[0].agent == "intent_router"
    assert llm.requests[0].run_id == run.run_id
    assert llm.requests[0].system == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_intent_router_falls_back_on_bad_output() -> None:
    for bad in ("not-json", None, [1, 2], 42, {"mode": "bogus"}):
        agent = IntentRouterAgent(FakeLLM(bad))
        run = ResearchRun(domain="seismic_event_classification", question="我想用多通道波形+时频图融合区分地震和爆破", constraints=ResearchConstraints())
        result = await agent.run(run)
        assert result["mode"] in {"discovery", "idea_refinement", "experiment_assistance"}
        assert result["required_inputs"]


@pytest.mark.asyncio
async def test_intent_router_fallback_keyword_heuristic() -> None:
    agent = IntentRouterAgent(FakeLLM(None))
    idea = ResearchRun(domain="x", question="我想用一个新方法融合波形", constraints=ResearchConstraints())
    assert (await agent.run(idea))["mode"] == "idea_refinement"
    exp = ResearchRun(domain="x", question="我已有 CNN 代码和训练结果，帮我补 baseline", constraints=ResearchConstraints())
    assert (await agent.run(exp))["mode"] == "experiment_assistance"
    disc = ResearchRun(domain="x", question="研究深度学习在地震识别中的应用", constraints=ResearchConstraints())
    assert (await agent.run(disc))["mode"] == "discovery"
