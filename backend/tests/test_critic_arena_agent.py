import pytest

from app.agents.critic_arena_agent import CriticArenaAgent, PERSPECTIVES
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import Hypothesis


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


def _hypotheses() -> list[Hypothesis]:
    return [
        Hypothesis(hypothesis_id="H1", statement="s1", rationale="r", novelty_claim="n", verification_path="v"),
        Hypothesis(hypothesis_id="H2", statement="s2", rationale="r", novelty_claim="n", verification_path="v"),
    ]


@pytest.mark.asyncio
async def test_critic_arena_runs_three_perspectives_in_parallel() -> None:
    llm = FakeLLM({
        "reviews": [
            {"hypothesis_id": "H1", "novelty": 9, "verifiability": 8, "self_consistency": 8,
             "data_availability": 7, "feasibility": 8, "evidence_support": 7, "reproducibility": 8,
             "competition_fit": 8, "risk": "r", "revision_advice": "a"},
            {"hypothesis_id": "H2", "novelty": 6, "verifiability": 7, "self_consistency": 7,
             "data_availability": 6, "feasibility": 7, "evidence_support": 6, "reproducibility": 7,
             "competition_fit": 6, "risk": "r", "revision_advice": "a"},
        ]
    })
    agent = CriticArenaAgent(llm)
    scores = await agent.arun(_hypotheses(), [], run_id="run_x")

    assert set(scores.keys()) == set(PERSPECTIVES)
    assert set(scores["domain_scientist"].keys()) == {"H1", "H2"}
    assert scores["domain_scientist"]["H1"].novelty == 9
    # 3 perspectives each made one LLM call (parallel).
    assert len(llm.requests) == 3
    assert {r.agent for r in llm.requests} == {"critic_arena"}


@pytest.mark.asyncio
async def test_critic_arena_falls_back_on_bad_output() -> None:
    agent = CriticArenaAgent(FakeLLM("garbage"))
    scores = await agent.arun(_hypotheses(), [], run_id="run_x")
    assert set(scores.keys()) == set(PERSPECTIVES)
    # Fallback still scores every hypothesis.
    for perspective in PERSPECTIVES:
        assert set(scores[perspective].keys()) == {"H1", "H2"}
        assert scores[perspective]["H1"].novelty > 0
