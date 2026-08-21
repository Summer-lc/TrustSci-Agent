# backend/tests/test_paper_type_classifier_agent.py
import pytest

from app.agents.paper_type_classifier_agent import PaperTypeClassifierAgent
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.paper import Paper


class FakeLLM:
    provider = "fake"
    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []
    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


def _papers() -> list[Paper]:
    return [
        Paper(paper_id="p1", title="EQTransformer: deep learning model", abstract="We propose a model."),
        Paper(paper_id="p2", title="STEAD: a global dataset", abstract="We introduce a dataset."),
        Paper(paper_id="p3", title="A survey of seismic ML", abstract="We review."),
    ]


@pytest.mark.asyncio
async def test_classifier_assigns_roles() -> None:
    llm = FakeLLM({"papers": [
        {"paper_id": "p1", "paper_role": "method_model", "baseline_eligible": True, "reason": "proposes a model"},
        {"paper_id": "p2", "paper_role": "dataset_benchmark", "baseline_eligible": False, "reason": "is a dataset"},
        {"paper_id": "p3", "paper_role": "survey_review", "baseline_eligible": False, "reason": "is a survey"},
    ]})
    agent = PaperTypeClassifierAgent(llm)
    out = await agent.arun(_papers(), run_id="run_x")
    by_id = {p.paper_id: p for p in out}
    assert by_id["p1"].paper_role == "method_model" and by_id["p1"].baseline_eligible is True
    assert by_id["p1"].seismic_relevant is True
    assert by_id["p2"].paper_role == "dataset_benchmark" and by_id["p2"].baseline_eligible is False
    assert by_id["p2"].baseline_rejection_reason == "is a dataset"
    assert by_id["p3"].baseline_eligible is False
    assert llm.requests[0].agent == "paper_classifier"


@pytest.mark.asyncio
async def test_classifier_falls_back_on_bad_output() -> None:
    agent = PaperTypeClassifierAgent(FakeLLM("garbage"))
    out = await agent.arun(_papers(), run_id="run_x")
    # Fallback: STEAD (dataset in title) -> dataset_benchmark/eligible False; survey -> survey_review; EQTransformer -> method_model
    by_id = {p.paper_id: p for p in out}
    assert by_id["p1"].baseline_eligible is True
    assert by_id["p2"].baseline_eligible is False
    assert by_id["p3"].baseline_eligible is False


@pytest.mark.asyncio
async def test_classifier_excludes_generic_ml_method_even_if_llm_calls_it_method() -> None:
    paper = Paper(
        paper_id="p_generic",
        title="Learning Active Subspaces and Discovering Important Features with Gaussian Radial Basis Functions Neural Networks",
        abstract="Providing a model that achieves predictive performance and is interpretable by humans.",
    )
    llm = FakeLLM({"papers": [
        {"paper_id": "p_generic", "paper_role": "method_model", "seismic_relevant": True, "reason": "model paper"},
    ]})
    out = await PaperTypeClassifierAgent(llm).arun([paper], run_id="run_x")
    assert out[0].paper_role == "method_model"
    assert out[0].seismic_relevant is False
    assert out[0].baseline_eligible is False
    assert "not seismic" in (out[0].baseline_rejection_reason or "")
