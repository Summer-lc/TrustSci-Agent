import pytest

from app.agents.novelty_checker_agent import NoveltyCheckerAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.hypothesis import Hypothesis
from app.schemas.paper import Paper


class FakeLLM:
    provider = "fake"
    def __init__(self, content): self.content = content; self.requests = []
    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake", fallback_used=False)


def _hyp() -> Hypothesis:
    return Hypothesis(hypothesis_id="H1", statement="Multi-channel spectral features for seismic event classification.",
                      rationale="freq separates classes", novelty_claim="spectral multi-channel",
                      verification_path="train/eval")


def _papers() -> list[Paper]:
    return [Paper(paper_id="p1", title="Spectral CNN for earthquake detection", code_url=None, doi="10.1/x")]


@pytest.mark.asyncio
async def test_novelty_checker_already_done_verdict() -> None:
    a = NoveltyCheckerAgent(FakeLLM({"verdict": "already_done", "claim_revision": None,
                                     "prior_art_paper_ids": ["p1"],
                                     "overlap_points": ["same task+method"],
                                     "retainable_novelty": [], "reasoning": "p1 already does this"}))
    v = await a.arun(_papers(), _hyp(), None, run_id="r")
    assert v.verdict == "already_done"
    assert v.prior_art_paper_ids == ["p1"]
    assert a.requests[0].agent == "novelty_checker"


@pytest.mark.asyncio
async def test_novelty_checker_transfer_applicability_with_claim_revision() -> None:
    a = NoveltyCheckerAgent(FakeLLM({"verdict": "transfer_applicability",
                                     "claim_revision": "A transfer-applicability study of spectral features to seismic event classification.",
                                     "prior_art_paper_ids": [], "overlap_points": [],
                                     "retainable_novelty": ["seismic-specific evaluation"], "reasoning": "method done in audio"}))
    v = await a.arun(_papers(), _hyp(), None, run_id="r")
    assert v.verdict == "transfer_applicability"
    assert v.claim_revision is not None
    assert "transfer" in v.claim_revision.lower()


@pytest.mark.asyncio
async def test_novelty_checker_falls_back_on_garbage() -> None:
    a = NoveltyCheckerAgent(FakeLLM("not json"))
    v = await a.arun(_papers(), _hyp(), None, run_id="r")
    # Fallback: no prior art found in deterministic pass -> novel (safe default)
    assert v.verdict in {"novel", "dataset_only"}
