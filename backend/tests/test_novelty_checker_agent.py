import pytest

from app.agents.novelty_checker_agent import NoveltyCheckerAgent, SYSTEM_PROMPT
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


def _papers() -> list[Paper]:
    return [Paper(paper_id="p1", title="Seismic event classification with CNN", code_url="https://github.com/x/y")]


@pytest.mark.asyncio
async def test_novelty_checker_returns_report() -> None:
    llm = FakeLLM({
        "verdict": "similar_work",
        "claim_revision": None,
        "prior_art_paper_ids": [],
        "similar_work": [{"title": "Seismic CNN", "code_url": "https://github.com/x/y"}],
        "has_public_code": True,
        "overlap_points": ["CNN on waveforms"],
        "retainable_novelty": ["multi-channel fusion"],
        "claims_to_downgrade": ["novelty of CNN baseline"],
        "optimization_directions": ["add spectrogram branch"],
        "reasoning": "similar work exists",
    })
    agent = NoveltyCheckerAgent(llm)
    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints())
    report = await agent.arun(_papers(), None, None, run_id=run.run_id)
    assert report.has_public_code is True
    assert report.retainable_novelty == ["multi-channel fusion"]
    assert llm.requests[0].agent == "novelty_checker"
    assert llm.requests[0].system == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_novelty_checker_falls_back_on_bad_output() -> None:
    for bad in ("nope", None, [1], 5, {"has_public_code": "x"}):
        agent = NoveltyCheckerAgent(FakeLLM(bad))
        report = await agent.arun(_papers(), None, None, run_id="run_x")
        assert isinstance(report.similar_work, list)
        assert isinstance(report.retainable_novelty, list)
