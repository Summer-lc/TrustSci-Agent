import pytest

from app.agents.planner_agent import PlannerAgent
from app.config import Settings
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.run import ResearchConstraints, ResearchRun
from app.tools.llm_logger import read_llm_logs
from app.tools.qwen_client import QwenClient


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            content=self.content,
            provider=self.provider,
            model="fake-model",
            fallback_used=False,
        )


@pytest.mark.asyncio
async def test_planner_agent_returns_structured_plan() -> None:
    llm = FakeLLM(
        {
            "research_objective": "Explain solid electrolyte conductivity.",
            "domain": "energy_materials",
            "sub_questions": ["Which mechanisms matter?"],
            "search_queries": ["solid electrolyte ionic conductivity mechanism"],
            "workflow_plan": ["retrieve papers", "verify citations"],
            "tools_to_call": ["openalex_search", "crossref_verify"],
        }
    )
    agent = PlannerAgent(llm)
    run = ResearchRun(
        domain="energy_materials",
        question="Generate a verifiable solid-state electrolyte hypothesis.",
        constraints=ResearchConstraints(max_papers=3, enable_browser_worker=True),
    )

    plan = await agent.run(run)

    assert plan["research_objective"] == "Explain solid electrolyte conductivity."
    assert plan["search_queries"] == ["solid electrolyte ionic conductivity mechanism"]
    assert "crossref_verify" in plan["tools_to_call"]
    assert "evidence_requirements" in plan
    assert "enable_browser_worker: True" in llm.requests[0].user


@pytest.mark.asyncio
async def test_planner_agent_falls_back_for_invalid_llm_content() -> None:
    agent = PlannerAgent(FakeLLM("not-json"))
    run = ResearchRun(
        domain="energy_materials",
        question="Plan a materials research workflow.",
        constraints=ResearchConstraints(max_papers=2),
    )

    plan = await agent.run(run)

    assert len(plan["sub_questions"]) >= 3
    assert len(plan["search_queries"]) >= 3
    assert "experiment_design" in " ".join(plan["workflow_plan"])


@pytest.mark.asyncio
async def test_planner_agent_acceptance_with_qwen_fallback_logs_call(tmp_path) -> None:
    run = ResearchRun(
        domain="energy_materials",
        question="提升固态电解质材料中离子电导率的潜在机制",
        constraints=ResearchConstraints(max_papers=2),
    )
    agent = PlannerAgent(QwenClient(Settings(dashscope_api_key="", data_dir=tmp_path)))

    plan = await agent.run(run)

    assert plan["search_queries"]
    assert plan["sub_questions"]
    assert plan["workflow_plan"]
    assert all(isinstance(item, str) and item for item in plan["search_queries"])
    assert all(isinstance(item, str) and item for item in plan["sub_questions"])
    assert all(isinstance(item, str) and item for item in plan["workflow_plan"])

    logs = read_llm_logs(tmp_path, run.run_id)
    assert len(logs) == 1
    assert logs[0]["agent"] == "planner"
    assert logs[0]["status"] == "fallback"
    assert logs[0]["system_prompt"]
    assert "提升固态电解质材料" in logs[0]["user_prompt"]
    assert logs[0]["response"]["search_queries"]
    assert logs[0]["response"]["sub_questions"]
    assert logs[0]["response"]["workflow_plan"]
