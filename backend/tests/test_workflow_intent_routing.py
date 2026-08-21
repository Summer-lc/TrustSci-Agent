import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content

    async def complete(self, request):
        from app.llm.interface import LLMResponse
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


@pytest.mark.asyncio
async def test_route_intent_sets_intent_and_idea_brief_for_refinement() -> None:
    settings = Settings(dashscope_api_key="")
    workflow = ScientistWorkflow(settings)
    workflow.intent_router = type(workflow.intent_router)(FakeLLM({"mode": "idea_refinement", "confidence": 0.9, "reason": "r", "required_inputs": ["question", "idea"]}))
    workflow.idea_intake = type(workflow.idea_intake)(FakeLLM({"research_problem": "p", "user_idea": "fusion", "target_task": "t", "target_labels": ["earthquake"]}))
    run = ResearchRun(domain="seismic_event_classification", question="我想用融合方法", constraints=ResearchConstraints(), mode="idea_refinement")

    await workflow._route_intent(run)

    assert run.intent["mode"] == "idea_refinement"
    assert run.idea_brief is not None
    assert run.idea_brief.user_idea == "fusion"


@pytest.mark.asyncio
async def test_route_intent_skips_idea_intake_for_discovery() -> None:
    settings = Settings(dashscope_api_key="")
    workflow = ScientistWorkflow(settings)
    run = ResearchRun(domain="seismic_event_classification", question="研究深度学习在地震识别中的应用", constraints=ResearchConstraints(), mode="discovery")

    await workflow._route_intent(run)

    assert run.intent["mode"] in {"discovery", "idea_refinement", "experiment_assistance"}
    assert run.idea_brief is None  # discovery does not run idea intake


@pytest.mark.asyncio
async def test_profile_scientific_data_branches_for_seismic() -> None:
    settings = Settings(dashscope_api_key="")
    workflow = ScientistWorkflow(settings)
    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(), mode="discovery")

    await workflow._profile_scientific_data(run)

    assert run.seismic_data_profile is not None
    assert run.seismic_data_profile.num_events > 0
