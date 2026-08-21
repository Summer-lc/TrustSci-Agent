# backend/tests/test_code_writer_agent.py
import pytest

from app.agents.code_writer_agent import CodeWriterAgent, FALLBACK_MODEL_PY
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis


class FakeLLM:
    provider = "fake"
    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []
    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider,
                           model="fake-model", fallback_used=False)


def _hyp() -> Hypothesis:
    return Hypothesis(hypothesis_id="H1", statement="Multi-channel spectral features "
                      "outperform single-channel time-domain statistics for earthquake/explosion/noise.",
                      rationale="freq separates classes", novelty_claim="spectral multi-channel",
                      verification_path="train/eval on synthetic waveforms")


def _plan() -> ExperimentPlan:
    return ExperimentPlan(datasets=["seismic_demo"], source="synthetic", target="label",
                          baselines=["time-domain stats + LR"], metrics=["accuracy","macro_f1"],
                          experiment_steps=["extract spectral features","train","eval"],
                          expected_results="method > baseline")


@pytest.mark.asyncio
async def test_initial_returns_llm_source_when_valid() -> None:
    src = "```python\nclass SeismicModel:\n    def fit(self,X,y): return self\n    def predict(self,X): return ['earthquake']*len(X)\n```\n"
    a = CodeWriterAgent(FakeLLM(src))
    out = await a.arun("initial", _hyp(), _plan(), run_id="r")
    assert "class SeismicModel" in out
    assert "fit" in out and "predict" in out
    assert a.llm.requests[0].agent == "code_writer"


@pytest.mark.asyncio
async def test_initial_falls_back_on_garbage() -> None:
    a = CodeWriterAgent(FakeLLM("not code at all, just chatter"))
    out = await a.arun("initial", _hyp(), _plan(), run_id="r")
    assert out == FALLBACK_MODEL_PY
    assert "class SeismicModel" in out
    assert "LogisticRegression" in out


@pytest.mark.asyncio
async def test_initial_falls_back_on_non_string() -> None:
    a = CodeWriterAgent(FakeLLM({"weird": "dict"}))
    out = await a.arun("initial", _hyp(), _plan(), run_id="r")
    assert out == FALLBACK_MODEL_PY


@pytest.mark.asyncio
async def test_repair_uses_traceback_and_current_source() -> None:
    src = "```python\nclass SeismicModel:\n    def fit(self,X,y): return self\n    def predict(self,X): return ['noise']*len(X)\n```"
    a = CodeWriterAgent(FakeLLM(src))
    out = await a.arun("repair", _hyp(), _plan(),
                       current_source="class SeismicModel:\n    pass",
                       traceback="ValueError: bad shape", run_id="r")
    assert "class SeismicModel" in out
    assert a.llm.requests[0].agent == "code_writer"
    # the rendered repair prompt (LLMRequest.user) must surface the traceback
    assert "ValueError: bad shape" in a.llm.requests[0].user


@pytest.mark.asyncio
async def test_repair_falls_back_to_skeleton() -> None:
    a = CodeWriterAgent(FakeLLM(""))
    out = await a.arun("repair", _hyp(), _plan(), current_source="x", traceback="boom", run_id="r")
    assert out == FALLBACK_MODEL_PY


def test_fallback_model_is_interface_compliant() -> None:
    import numpy as np
    ns = {}
    exec(FALLBACK_MODEL_PY, ns)
    m = ns["SeismicModel"]()
    # ≥2 classes — LogisticRegression requires it; the real train split always
    # has 3 classes (60/35/25), so this mirrors the real loop.
    X = np.zeros((4, 3, 100))
    y = np.array(["earthquake", "explosion", "earthquake", "noise"])
    m.fit(X, y)
    pred = m.predict(X)
    assert len(pred) == 4
