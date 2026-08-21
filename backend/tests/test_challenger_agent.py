import pytest

from app.agents.challenger_agent import ChallengerAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.idea import IdeaBrief
from app.schemas.hypothesis import Hypothesis


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


def _main() -> Hypothesis:
    return Hypothesis(hypothesis_id="H_main", statement="fuse multi-channel waveform with spectrogram",
                      rationale="r", novelty_claim="fusion", verification_path="v")


def _brief() -> IdeaBrief:
    return IdeaBrief(research_problem="seismic classification", user_idea="fuse waveform with spectrogram",
                     target_task="eq/explosion classification", input_data=["waveform", "spectrogram"],
                     target_labels=["earthquake", "explosion"])


@pytest.mark.asyncio
async def test_challenger_returns_three_ablation_challenges() -> None:
    llm = FakeLLM({"challenges": [
        {"challenge_id": "H_c1", "hypothesis_id": "H_c1", "statement": "waveform only", "rationale": "r",
         "novelty_claim": "no spectrogram", "verification_path": "v",
         "tests_innovation_point": "spectrogram branch", "expected_insight": "fusion > waveform-only",
         "derivation_from_main": "remove spectrogram branch"},
        {"challenge_id": "H_c2", "hypothesis_id": "H_c2", "statement": "spectrogram only", "rationale": "r",
         "novelty_claim": "no waveform", "verification_path": "v",
         "tests_innovation_point": "waveform channel", "expected_insight": "fusion > spectrogram-only",
         "derivation_from_main": "remove waveform branch"},
        {"challenge_id": "H_c3", "hypothesis_id": "H_c3", "statement": "concat instead of fusion", "rationale": "r",
         "novelty_claim": "simple concat", "verification_path": "v",
         "tests_innovation_point": "fusion module", "expected_insight": "fusion > concat",
         "derivation_from_main": "replace fusion module with concat"},
    ]})
    agent = ChallengerAgent(llm)
    challengers, design = await agent.arun(_main(), _brief(), run_id="run_x")
    assert len(challengers) == 3
    assert {c.hypothesis_id for c in challengers} == {"H_c1", "H_c2", "H_c3"}
    assert len(design) == 3
    assert design[0].tests_innovation_point == "spectrogram branch"
    assert llm.requests[0].agent == "challenger"


@pytest.mark.asyncio
async def test_challenger_falls_back_on_bad_output() -> None:
    agent = ChallengerAgent(FakeLLM("nope"))
    challengers, design = await agent.arun(_main(), _brief(), run_id="run_x")
    assert len(challengers) == 3
    assert len(design) == 3
