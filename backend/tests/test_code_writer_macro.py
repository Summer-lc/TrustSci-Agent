# backend/tests/test_code_writer_macro.py
import pytest

from app.agents.code_writer_agent import CodeWriterAgent, FALLBACK_MODEL_PY
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis


class FakeLLM:
    provider = "fake"
    def __init__(self, content): self.content = content; self.requests = []
    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake", fallback_used=False)


def _hyp() -> Hypothesis:
    return Hypothesis(hypothesis_id="H1", statement="spectral features", rationale="r",
                      novelty_claim="n", verification_path="v")


def _plan() -> ExperimentPlan:
    return ExperimentPlan(datasets=["d"], source="s", target="t", baselines=["b"],
                          metrics=["accuracy"], experiment_steps=["x"], expected_results="e")


@pytest.mark.asyncio
async def test_macro_mode_returns_rewritten_architecture() -> None:
    src = "```python\nclass SeismicModel:\n    def fit(self,X,y): return self\n    def predict(self,X): return ['noise']*len(X)\n```"
    a = CodeWriterAgent(FakeLLM(src))
    out = await a.arun("macro", _hyp(), _plan(),
                       current_source="class SeismicModel:\n    pass",
                       last_metrics={"accuracy": 0.4}, last_comparison={"method_beats_baseline": False},
                       notes=["method below baseline"], run_id="r")
    assert "class SeismicModel" in out
    assert a.llm.requests[0].agent == "code_writer"
    # macro prompt must surface the metrics so the LLM can diagnose
    assert "0.4" in a.llm.requests[0].user


@pytest.mark.asyncio
async def test_macro_mode_falls_back_on_garbage() -> None:
    a = CodeWriterAgent(FakeLLM("garbage"))
    out = await a.arun("macro", _hyp(), _plan(), current_source="x",
                       last_metrics={"accuracy": 0.3}, last_comparison={}, notes=[], run_id="r")
    assert out == FALLBACK_MODEL_PY
