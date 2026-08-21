import pytest
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.agents.planner_agent import PlannerAgent, PlannerPlanParser, SYSTEM_PROMPT
from app.llm.interface import LLMRequest, LLMResponse
from app.llm.langchain_adapter import LLMClientRunnable
from app.schemas.run import ResearchConstraints, ResearchRun


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
async def test_llm_client_runnable_is_a_langchain_runnable() -> None:
    runnable = LLMClientRunnable(FakeLLM({}))
    assert isinstance(runnable, Runnable)


@pytest.mark.asyncio
async def test_llm_client_runnable_preserves_llmrequest_fields() -> None:
    llm = FakeLLM({"answer": 1})
    prompt = ChatPromptTemplate.from_messages([("system", "SYS"), ("user", "Domain: {domain}")])
    chain = prompt | LLMClientRunnable(llm).bind(
        fallback={"fb": True}, run_id="run_x", agent="planner"
    )

    content = await chain.ainvoke({"domain": "energy_materials"})

    assert content == {"answer": 1}
    assert len(llm.requests) == 1
    request = llm.requests[0]
    assert request.system == "SYS"
    assert request.user == "Domain: energy_materials"
    assert request.agent == "planner"
    assert request.run_id == "run_x"
    assert request.fallback == {"fb": True}
    assert request.response_format.value == "json"


@pytest.mark.asyncio
async def test_planner_agent_uses_langchain_chain_and_preserves_request() -> None:
    llm = FakeLLM(
        {
            "research_objective": "Explain solid electrolyte conductivity.",
            "domain": "energy_materials",
            "sub_questions": ["Which mechanisms matter?"],
            "search_queries": ["solid electrolyte ionic conductivity mechanism"],
            "workflow_plan": ["retrieve papers", "verify citations"],
            "tools_to_call": ["literature_router", "layered_citation_verifier"],
            "perspectives": [
                {
                    "perspective": "domain_mechanism",
                    "role": "Materials scientist",
                    "question": "Which mechanisms matter?",
                    "search_query": "solid electrolyte mechanism",
                    "evidence_requirement": "Mechanism claims need verified papers.",
                    "risk_control": "Avoid unsupported causal claims.",
                }
            ],
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
    assert plan["perspectives"][0]["role"] == "Materials scientist"

    # The LangChain chain still produces a full LLMRequest identical to the old
    # direct self.llm.complete() call (system prompt, run_id, agent, user text).
    assert len(llm.requests) == 1
    request = llm.requests[0]
    assert request.agent == "planner"
    assert request.run_id == run.run_id
    assert request.system == SYSTEM_PROMPT
    assert "enable_browser_worker: True" in request.user
    assert "enable_arxiv: True" in request.user
    assert run.question in request.user


@pytest.mark.asyncio
async def test_planner_chain_falls_back_and_never_crashes() -> None:
    base = ResearchRun(
        domain="energy_materials",
        question="Plan a materials research workflow.",
        constraints=ResearchConstraints(max_papers=2),
    )

    # Non-dict / invalid LLM outputs all fall back without raising.
    for bad_content in ("not-json", None, [1, 2, 3], 42, {"perspectives": "nope"}):
        agent = PlannerAgent(FakeLLM(bad_content))
        plan = await agent.run(base.model_copy(deep=True))
        assert plan["sub_questions"]
        assert plan["search_queries"]
        assert plan["workflow_plan"]
        assert plan["perspectives"]


def test_planner_parser_returns_fallback_when_normalize_raises(monkeypatch) -> None:
    import app.agents.planner_agent as planner_module

    def boom(content, fallback):  # noqa: ANN001 - simulate a parser/validator failure
        raise RuntimeError("simulated parser failure")

    monkeypatch.setattr(planner_module, "_normalize_plan", boom)
    fallback = {"research_objective": "fb", "domain": "fb"}
    parser = PlannerPlanParser(fallback=fallback)

    # Even when normalization raises, the parser returns the fallback instead of
    # propagating the exception (run never crashes on malformed model output).
    result = parser.parse({"anything": "x"})
    assert result == fallback
