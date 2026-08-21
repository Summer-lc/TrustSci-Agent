# v3 Sprint S1 实施计划：地基收尾 + Intent Router 分支（Layer 0）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏 v1/v2 线性闭环的前提下，落地 v3 的数据契约（ResearchMode / IdeaBrief / SeismicDataProfile）、IntentRouter 与 IdeaIntake 两个 LCEL agent、地震 demo subset，并在 LangGraph 图前部加入 `intent_router` conditional edge（三分支 placeholder），让前端 Mode Selector 接通后端 `mode` 字段。

**Architecture:** 复用现有 LCEL 模式（`PlannerAgent` 的 `PROMPT | LLMClientRunnable.bind(...) | Parser`）。IntentRouter/IdeaIntake 是 engine-agnostic agent；`ScientistWorkflow._route_intent` 作为共享首步供 classic 与 LangGraph 两个引擎调用；`LangGraphWorkflow` 额外把 intent_router 包成图节点 + 三个 placeholder 分支节点 + `add_conditional_edges`。地震数据走独立 `SeismicDataAdapter`，`_profile_scientific_data` 按 domain 分支。

**Tech Stack:** Python 3.11 / FastAPI / Pydantic / LangChain（LCEL + `LLMClientRunnable`）/ LangGraph StateGraph / pytest / Next.js + TypeScript。

## Global Constraints

- 所有新 LLM agent 必须走 `LLMClientRunnable` 适配器（仍调 `QwenClient.complete()`），保留 `data/outputs/llm_calls` 审计日志；`agent` 字段用各自名字（`intent_router` / `idea_intake`）。
- 任何 malformed LLM 输出必须落 fallback，不得崩溃 run（照 `PlannerAgent` 的 `Parser` 模式）。
- 不带 `DASHSCOPE_API_KEY` 时走确定性 demo fallback（关键词启发式）。
- v1/v2 经典流程与现有测试必须继续通过；新增 `intent_router` 步骤会出现在 `run.steps` 首位，相关断言需同步更新。
- YAGNI：S1 只创建 S1 实际消费的 schema（`ResearchMode` / `IdeaBrief` / `SeismicDataProfile`）。`BaselineCandidate`（S2）、`HypothesisArenaResult`（S3）、`ExperimentSpec/Run/CodeDebugIteration/ExperimentIteration`（S4/S5）等 schema 与对应 `ResearchRun` 字段推迟到各自 Sprint 创建，不在 S1 提前落地。`WorkflowState` 本 Sprint 不新增 channel（`mode` 已在 `run` 上，`arena_result/iteration/debug_iteration/messages` 推迟到 S3/S4 节点真正需要时再加）。
- 文件路径均为相对仓库根 `d:/For work/TrustSci-Agent/`。
- 后端测试运行：`cd backend && python -m pytest tests/<file>::<test> -v`（项目用 `python -m pytest`）。

## File Structure

- **Create** `backend/app/schemas/mode.py` — `ResearchMode` Literal 类型。
- **Create** `backend/app/schemas/idea.py` — `IdeaBrief` Pydantic 模型（PRD §11.2）。
- **Create** `backend/app/schemas/seismic.py` — `SeismicDataProfile` Pydantic 模型（PRD §6.3）。
- **Create** `backend/app/agents/intent_router_agent.py` — IntentRouter LCEL agent + Parser + fallback。
- **Create** `backend/app/agents/idea_intake_agent.py` — IdeaIntake LCEL agent + Parser + fallback。
- **Create** `backend/app/tools/seismic_data.py` — `SeismicDataAdapter`，读 demo subset 生成 profile。
- **Create** `experiments/seismic_event_classification/data/prepare_dataset.py` — 确定性生成 demo subset。
- **Create** `data/seismic_demo/events.csv` — 由 prepare_dataset.py 生成并提交（测试依赖此文件存在）。
- **Create** `backend/tests/test_intent_router_agent.py`
- **Create** `backend/tests/test_idea_intake_agent.py`
- **Create** `backend/tests/test_seismic_data_adapter.py`
- **Modify** `backend/app/schemas/run.py` — `ResearchRun` 加 `mode/idea_brief/intent/seismic_data_profile`；`ResearchRunCreate` 加 `mode`。
- **Modify** `backend/app/workflows/scientist_workflow.py` — `__init__` 装配三个新组件；新增 `_route_intent`；`run()` 首步插 intent_router；`_profile_scientific_data` 按 seismic domain 分支。
- **Modify** `backend/app/workflows/langgraph_workflow.py` — `_build_graph` 加 intent_router 节点 + 三分支 placeholder + conditional_edges；`_route_entry` fresh 路径改走 intent_router；新增 `_node_passthrough` 与 `_route_by_mode`。
- **Modify** `backend/app/api/routes_runs.py` — `create_run` 透传 `mode`。
- **Modify** `backend/tests/test_langgraph_workflow.py` — step_names 断言加入 `intent_router`。
- **Modify** `frontend/lib/api.ts` — `createRun` 加 `mode` 参数；`ResearchRun` 类型加 `mode/idea_brief/seismic_data_profile`。
- **Modify** `frontend/components/workbench/Workbench.tsx` — `handleStart` 传 `draft.researchMode`。

---

### Task 1: v3 基础 schema 与 ResearchRun 字段

**Files:**
- Create: `backend/app/schemas/mode.py`
- Create: `backend/app/schemas/idea.py`
- Create: `backend/app/schemas/seismic.py`
- Modify: `backend/app/schemas/run.py`
- Test: `backend/tests/test_v3_schemas.py` (create)

**Interfaces:**
- Produces: `ResearchMode` (Literal type, importable from `app.schemas.mode`); `IdeaBrief` (from `app.schemas.idea`); `SeismicDataProfile` (from `app.schemas.seismic`). `ResearchRun.mode: ResearchMode`, `ResearchRun.idea_brief: IdeaBrief | None`, `ResearchRun.intent: dict | None`, `ResearchRun.seismic_data_profile: SeismicDataProfile | None`. `ResearchRunCreate.mode: ResearchMode`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_v3_schemas.py
from app.schemas.idea import IdeaBrief
from app.schemas.mode import ResearchMode
from app.schemas.run import ResearchConstraints, ResearchRun, ResearchRunCreate
from app.schemas.seismic import SeismicDataProfile


def test_research_run_defaults_mode_to_discovery() -> None:
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    assert run.mode == "discovery"
    assert run.idea_brief is None
    assert run.intent is None
    assert run.seismic_data_profile is None


def test_research_run_create_carries_mode() -> None:
    payload = ResearchRunCreate(domain="seismic_event_classification", question="q", mode="idea_refinement")
    run = ResearchRun(domain=payload.domain, question=payload.question, constraints=payload.constraints, mode=payload.mode)
    assert run.mode == "idea_refinement"


def test_idea_brief_round_trip() -> None:
    brief = IdeaBrief(
        research_problem="地震事件分类",
        user_idea="多通道波形与时频图融合",
        target_task="earthquake/explosion/noise classification",
        input_data=["three-component waveform", "spectrogram"],
        target_labels=["earthquake", "explosion", "noise"],
    )
    dumped = brief.model_dump()
    assert dumped["user_idea"] == "多通道波形与时频图融合"
    assert dumped["target_labels"] == ["earthquake", "explosion", "noise"]


def test_seismic_data_profile_defaults() -> None:
    profile = SeismicDataProfile(dataset_name="demo", num_events=10)
    assert profile.labels == {}
    assert profile.split_strategy == "event_level"
    assert profile.risks == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_v3_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.schemas.mode'`

- [ ] **Step 3: Write the schemas**

```python
# backend/app/schemas/mode.py
from typing import Literal

ResearchMode = Literal["discovery", "idea_refinement", "experiment_assistance"]
```

```python
# backend/app/schemas/idea.py
from pydantic import BaseModel, Field


class IdeaBrief(BaseModel):
    research_problem: str
    user_idea: str | None = None
    target_task: str
    input_data: list[str] = Field(default_factory=list)
    proposed_method: str | None = None
    expected_contribution: str | None = None
    target_labels: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
```

```python
# backend/app/schemas/seismic.py
from pydantic import BaseModel, Field


class SeismicDataProfile(BaseModel):
    dataset_name: str
    num_events: int
    labels: dict[str, int] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=list)
    sampling_rate: int | None = None
    window_seconds: int | None = None
    split_strategy: str = "event_level"
    risks: list[str] = Field(default_factory=list)
    source_path: str | None = None
```

Now modify `backend/app/schemas/run.py`. Add imports after line 16 (`from app.schemas.planner import PerspectiveQuestion`):

```python
from app.schemas.idea import IdeaBrief
from app.schemas.mode import ResearchMode
from app.schemas.seismic import SeismicDataProfile
```

Add `mode` to `ResearchRunCreate` (after `question: str`):

```python
class ResearchRunCreate(BaseModel):
    domain: str = "energy_materials"
    question: str
    mode: ResearchMode = "discovery"
    constraints: ResearchConstraints = Field(default_factory=ResearchConstraints)
```

Add four fields to `ResearchRun` (after `question: str` / `constraints` block, before `status`):

```python
    mode: ResearchMode = "discovery"
    idea_brief: IdeaBrief | None = None
    intent: dict | None = None
    seismic_data_profile: SeismicDataProfile | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_v3_schemas.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/mode.py backend/app/schemas/idea.py backend/app/schemas/seismic.py backend/app/schemas/run.py backend/tests/test_v3_schemas.py
git commit -m "feat(v3-s1): add ResearchMode/IdeaBrief/SeismicDataProfile schemas and ResearchRun fields"
```

---

### Task 2: IntentRouterAgent（LCEL）

**Files:**
- Create: `backend/app/agents/intent_router_agent.py`
- Test: `backend/tests/test_intent_router_agent.py`

**Interfaces:**
- Consumes: `LLMClient` (`app.llm.interface`), `LLMClientRunnable` (`app.llm.langchain_adapter`), `ResearchRun` (`app.schemas.run`).
- Produces: `IntentRouterAgent.run(run: ResearchRun) -> dict` returning `{mode: str, confidence: float, reason: str, required_inputs: list[str]}`. The workflow (Task 6) stores this dict on `run.intent` and uses `run.mode` (user-set) for routing; the agent's inferred `mode` is for audit/display.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_intent_router_agent.py
import pytest

from app.agents.intent_router_agent import IntentRouterAgent, SYSTEM_PROMPT
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.run import ResearchConstraints, ResearchRun


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


@pytest.mark.asyncio
async def test_intent_router_returns_llm_mode() -> None:
    llm = FakeLLM({"mode": "idea_refinement", "confidence": 0.9, "reason": "user proposes a method", "required_inputs": ["question", "idea"]})
    agent = IntentRouterAgent(llm)
    run = ResearchRun(domain="seismic_event_classification", question="我想用多通道波形+时频图融合区分地震和爆破", constraints=ResearchConstraints())
    result = await agent.run(run)
    assert result["mode"] == "idea_refinement"
    assert result["required_inputs"] == ["question", "idea"]
    assert llm.requests[0].agent == "intent_router"
    assert llm.requests[0].run_id == run.run_id
    assert llm.requests[0].system == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_intent_router_falls_back_on_bad_output() -> None:
    for bad in ("not-json", None, [1, 2], 42, {"mode": "bogus"}):
        agent = IntentRouterAgent(FakeLLM(bad))
        run = ResearchRun(domain="seismic_event_classification", question="我想用多通道波形+时频图融合区分地震和爆破", constraints=ResearchConstraints())
        result = await agent.run(run)
        assert result["mode"] in {"discovery", "idea_refinement", "experiment_assistance"}
        assert result["required_inputs"]


@pytest.mark.asyncio
async def test_intent_router_fallback_keyword_heuristic() -> None:
    agent = IntentRouterAgent(FakeLLM(None))
    idea = ResearchRun(domain="x", question="我想用一个新方法融合波形", constraints=ResearchConstraints())
    assert (await agent.run(idea))["mode"] == "idea_refinement"
    exp = ResearchRun(domain="x", question="我已有 CNN 代码和训练结果，帮我补 baseline", constraints=ResearchConstraints())
    assert (await agent.run(exp))["mode"] == "experiment_assistance"
    disc = ResearchRun(domain="x", question="研究深度学习在地震识别中的应用", constraints=ResearchConstraints())
    assert (await agent.run(disc))["mode"] == "discovery"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_intent_router_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.intent_router_agent'`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/intent_router_agent.py
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable
from app.schemas.mode import ResearchMode
from app.schemas.run import ResearchRun

SYSTEM_PROMPT = """You are the Intent Router Agent for TrustSci-Agent v3.
Classify the user's research input into exactly one of three entry modes.

Modes:
- discovery: the user only has a fuzzy research direction and no concrete method or code.
- idea_refinement: the user already proposes a concrete method/idea to be validated.
- experiment_assistance: the user already has data, code, or results and wants baselines/ablations/reporting filled in.

Return JSON only with keys:
- mode: one of "discovery", "idea_refinement", "experiment_assistance"
- confidence: float in [0,1]
- reason: one sentence why this mode fits
- required_inputs: list of input kinds the downstream workflow needs (e.g. ["question"], ["question","idea"], ["question","data_path","code_path"])
"""

USER_TEMPLATE = """Domain: {domain}
Question: {question}
Mode hint from UI: {mode_hint}

Classify the research entry mode. Do not invent references or results."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)])

_VALID_MODES = {"discovery", "idea_refinement", "experiment_assistance"}


class IntentRouterResultParser(Runnable):
    def __init__(self, fallback: dict) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> dict:
        try:
            return _normalize(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> dict:
        return self.parse(input)


class IntentRouterAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, run: ResearchRun) -> dict:
        fallback = _fallback_intent(run)
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback, run_id=run.run_id, agent="intent_router")
            | IntentRouterResultParser(fallback=fallback)
        )
        return await chain.ainvoke(_prompt_vars(run))


def _prompt_vars(run: ResearchRun) -> dict:
    return {"domain": run.domain, "question": run.question, "mode_hint": run.mode}


def _normalize(content: object, fallback: dict) -> dict:
    if not isinstance(content, dict):
        return fallback
    mode = str(content.get("mode", "")).strip()
    if mode not in _VALID_MODES:
        return fallback
    required = content.get("required_inputs", fallback["required_inputs"])
    if not isinstance(required, list):
        required = fallback["required_inputs"]
    return {
        "mode": mode,
        "confidence": _float(content.get("confidence", fallback["confidence"])),
        "reason": str(content.get("reason", fallback["reason"])).strip() or fallback["reason"],
        "required_inputs": [str(x) for x in required if str(x).strip()],
    }


def _float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _fallback_intent(run: ResearchRun) -> dict:
    q = run.question.lower()
    exp_keywords = ["已有代码", "已有数据", "已有结果", "已有实验", "already have", "existing code", "existing model", "补 baseline", "补消融"]
    idea_keywords = ["创意", "想法", "我想用", "我想提出", "my idea", "i propose", "propose"]
    if any(k in q for k in exp_keywords):
        mode: ResearchMode = "experiment_assistance"
        required = ["question", "data_path", "code_path"]
        reason = "User mentions existing code/data/results; treat as experiment assistance."
    elif any(k in q for k in idea_keywords):
        mode = "idea_refinement"
        required = ["question", "idea"]
        reason = "User proposes a concrete method; refine the idea."
    else:
        mode = "discovery"
        required = ["question"]
        reason = "Only a research direction is given; discover hypotheses from scratch."
    return {"mode": mode, "confidence": 0.5, "reason": reason, "required_inputs": required}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_intent_router_agent.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/intent_router_agent.py backend/tests/test_intent_router_agent.py
git commit -m "feat(v3-s1): add IntentRouterAgent LCEL chain with keyword fallback"
```

---

### Task 3: IdeaIntakeAgent（LCEL）

**Files:**
- Create: `backend/app/agents/idea_intake_agent.py`
- Test: `backend/tests/test_idea_intake_agent.py`

**Interfaces:**
- Consumes: `LLMClient`, `LLMClientRunnable`, `ResearchRun`, `IdeaBrief` (`app.schemas.idea`).
- Produces: `IdeaIntakeAgent.run(run: ResearchRun) -> IdeaBrief`. Workflow (Task 6) stores on `run.idea_brief` when `mode == "idea_refinement"`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_idea_intake_agent.py
import pytest

from app.agents.idea_intake_agent import IdeaIntakeAgent, SYSTEM_PROMPT
from app.llm.interface import LLMRequest, LLMResponse
from app.schemas.run import ResearchConstraints, ResearchRun


class FakeLLM:
    provider = "fake"

    def __init__(self, content):
        self.content = content
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, provider=self.provider, model="fake-model", fallback_used=False)


@pytest.mark.asyncio
async def test_idea_intake_returns_brief() -> None:
    llm = FakeLLM({
        "research_problem": "地震事件分类",
        "user_idea": "多通道波形与时频图融合",
        "target_task": "earthquake/explosion/noise classification",
        "input_data": ["three-component waveform", "spectrogram"],
        "target_labels": ["earthquake", "explosion", "noise"],
        "unknowns": ["公开数据是否包含目标标签"],
    })
    agent = IdeaIntakeAgent(llm)
    run = ResearchRun(domain="seismic_event_classification", question="我想用多通道波形+时频图融合区分地震和爆破", constraints=ResearchConstraints())
    brief = await agent.run(run)
    assert brief.user_idea == "多通道波形与时频图融合"
    assert brief.target_labels == ["earthquake", "explosion", "noise"]
    assert llm.requests[0].agent == "idea_intake"
    assert llm.requests[0].system == SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_idea_intake_falls_back_on_bad_output() -> None:
    for bad in ("nope", None, [1], 7, {"user_idea": "x"}):
        agent = IdeaIntakeAgent(FakeLLM(bad))
        run = ResearchRun(domain="seismic_event_classification", question="我想用一个新融合方法", constraints=ResearchConstraints())
        brief = await agent.run(run)
        assert brief.research_problem
        assert brief.target_task
        assert brief.user_idea is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_idea_intake_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.agents.idea_intake_agent'`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/idea_intake_agent.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import LLMClientRunnable
from app.schemas.idea import IdeaBrief
from app.schemas.run import ResearchRun

SYSTEM_PROMPT = """You are the Idea Intake Agent for TrustSci-Agent v3 (Idea Refinement mode).
Structure the user's concrete research idea into an IdeaBrief.
Return JSON only with keys:
- research_problem: str
- user_idea: str (the user's proposed method, verbatim in spirit)
- target_task: str
- input_data: list[str]
- proposed_method: str | null
- expected_contribution: str | null
- target_labels: list[str]
- unknowns: list[str]
- risks: list[str]
Do not invent citations, datasets, or results. Mark uncertain items in unknowns/risks."""

USER_TEMPLATE = """Domain: {domain}
Question: {question}

Structure the user's idea into an IdeaBrief JSON."""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", USER_TEMPLATE)])


class IdeaBriefParser(Runnable):
    def __init__(self, fallback: IdeaBrief) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> IdeaBrief:
        try:
            return _normalize(content, self.fallback)
        except Exception:
            return self.fallback

    def invoke(self, input: object, config: object = None, **kwargs: object) -> IdeaBrief:
        return self.parse(input)

    async def ainvoke(self, input: object, config: object = None, **kwargs: object) -> IdeaBrief:
        return self.parse(input)


class IdeaIntakeAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(self, run: ResearchRun) -> IdeaBrief:
        fallback = _fallback_brief(run)
        chain = (
            PROMPT
            | LLMClientRunnable(self.llm).bind(fallback=fallback.model_dump(), run_id=run.run_id, agent="idea_intake")
            | IdeaBriefParser(fallback=fallback)
        )
        return await chain.ainvoke({"domain": run.domain, "question": run.question})


def _normalize(content: object, fallback: IdeaBrief) -> IdeaBrief:
    if not isinstance(content, dict):
        return fallback
    payload = fallback.model_dump()
    payload.update(content)
    return IdeaBrief.model_validate(payload)


def _fallback_brief(run: ResearchRun) -> IdeaBrief:
    return IdeaBrief(
        research_problem=run.question,
        user_idea=run.question,
        target_task="earthquake/explosion/noise classification" if "seismic" in run.domain else run.question,
        input_data=["three-component waveform", "spectrogram"] if "seismic" in run.domain else [],
        target_labels=["earthquake", "explosion", "noise"] if "seismic" in run.domain else [],
        unknowns=["公开数据是否包含目标标签", "是否有相似已发表方法", "baseline 代码是否可复现"],
        risks=["创意创新点可能与已有工作重合", "公开数据标签不足"],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_idea_intake_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/idea_intake_agent.py backend/tests/test_idea_intake_agent.py
git commit -m "feat(v3-s1): add IdeaIntakeAgent LCEL chain with fallback"
```

---

### Task 4: 地震 demo subset + SeismicDataAdapter

**Files:**
- Create: `experiments/seismic_event_classification/data/prepare_dataset.py`
- Create: `data/seismic_demo/events.csv`
- Create: `backend/app/tools/seismic_data.py`
- Test: `backend/tests/test_seismic_data_adapter.py`

**Interfaces:**
- Produces: `SeismicDataAdapter(data_dir: Path).profile() -> SeismicDataProfile`. Reads `data_dir / "seismic_demo" / "events.csv"`. Workflow (Task 6) calls it when `run.domain == "seismic_event_classification"`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_seismic_data_adapter.py
from pathlib import Path

from app.tools.seismic_data import SeismicDataAdapter


def test_seismic_adapter_profiles_demo_subset(tmp_path: Path) -> None:
    # Copy the committed demo csv into a tmp data_dir so the test does not
    # depend on the repo working directory.
    demo_dir = tmp_path / "seismic_demo"
    demo_dir.mkdir()
    src = Path("data/seismic_demo/events.csv")
    (demo_dir / "events.csv").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    profile = SeismicDataAdapter(tmp_path).profile()

    assert profile.dataset_name == "demo_seismic_events"
    assert profile.num_events > 0
    assert set(profile.labels).issuperset({"earthquake", "explosion", "noise"})
    assert profile.sampling_rate == 100
    assert profile.window_seconds == 30
    assert profile.channels == ["Z", "N", "E"]
    assert profile.split_strategy == "event_level"
    assert profile.risks  # non-empty risk list
    assert profile.source_path and profile.source_path.endswith("events.csv")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_seismic_data_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError` or `FileNotFoundError` (csv/adapter missing).

- [ ] **Step 3: Generate the demo subset and write the adapter**

First create the generator:

```python
# experiments/seismic_event_classification/data/prepare_dataset.py
"""Generate the small deterministic seismic demo subset.

Produces data/seismic_demo/events.csv with event-level metadata. S1 only
profiles metadata; S4 will add waveform tensors. Run from repo root:

    python experiments/seismic_event_classification/data/prepare_dataset.py
"""
import csv
import random
from pathlib import Path

LABELS = ["earthquake", "explosion", "noise"]
STATIONS = ["STA01", "STA02", "STA03", "STA04"]
COUNTS = {"earthquake": 60, "explosion": 35, "noise": 25}  # 120 events
SAMPLING_RATE = 100
WINDOW_SECONDS = 30
CHANNELS = ["Z", "N", "E"]


def build_rows() -> list[dict]:
    rng = random.Random(20260629)
    rows: list[dict] = []
    event_id = 1
    for label, count in COUNTS.items():
        for _ in range(count):
            rows.append({
                "event_id": f"evt_{event_id:04d}",
                "label": label,
                "station": rng.choice(STATIONS),
                "sampling_rate": SAMPLING_RATE,
                "window_seconds": WINDOW_SECONDS,
                "channels": "/".join(CHANNELS),
                "split": "train" if event_id % 5 else ("val" if event_id % 3 == 0 else "test"),
            })
            event_id += 1
    return rows


def main() -> None:
    out_dir = Path("data/seismic_demo")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "events.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(build_rows()[0].keys()))
        writer.writeheader()
        writer.writerows(build_rows())
    print(f"wrote {path} with {sum(COUNTS.values())} events")


if __name__ == "__main__":
    main()
```

Generate the committed csv (run from repo root):

```bash
python experiments/seismic_event_classification/data/prepare_dataset.py
```

Then the adapter:

```python
# backend/app/tools/seismic_data.py
import csv
from collections import Counter
from pathlib import Path

from app.schemas.seismic import SeismicDataProfile

DEMO_DATASET_NAME = "demo_seismic_events"


class SeismicDataAdapter:
    """Profile the bundled seismic demo subset (S1: metadata only).

    S4 will extend this to read waveform tensors and produce train/val/test
    splits for the Code Experiment Loop. S1 only profiles event metadata so
    the workspace can show a seismic data profile before experiments exist.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def profile(self) -> SeismicDataProfile:
        path = self.data_dir / "seismic_demo" / "events.csv"
        rows = _read_csv(path)
        labels = dict(Counter(row["label"] for row in rows))
        channels = rows[0]["channels"].split("/") if rows and rows[0].get("channels") else []
        sampling_rate = int(rows[0]["sampling_rate"]) if rows and rows[0].get("sampling_rate") else None
        window_seconds = int(rows[0]["window_seconds"]) if rows and rows[0].get("window_seconds") else None
        risks = _risks(labels, rows)
        return SeismicDataProfile(
            dataset_name=DEMO_DATASET_NAME,
            num_events=len(rows),
            labels=labels,
            channels=channels or ["Z", "N", "E"],
            sampling_rate=sampling_rate,
            window_seconds=window_seconds,
            split_strategy="event_level",
            risks=risks,
            source_path=str(path),
        )


def _risks(labels: dict, rows: list[dict]) -> list[str]:
    risks: list[str] = []
    total = sum(labels.values()) or 1
    minority = [label for label, count in labels.items() if count / total < 0.15]
    if minority:
        risks.append(f"class imbalance: {', '.join(minority)} below 15% share")
    stations = {row.get("station") for row in rows}
    if len(stations) >= 2:
        risks.append("station leakage: ensure station-level split to test cross-station generalization")
    if "noise" in labels and labels.get("noise", 0) / total < 0.25:
        risks.append("minority class noise may need class weighting or resampling")
    return risks or ["no major risks detected in the demo subset"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_seismic_data_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add experiments/seismic_event_classification/data/prepare_dataset.py data/seismic_demo/events.csv backend/app/tools/seismic_data.py backend/tests/test_seismic_data_adapter.py
git commit -m "feat(v3-s1): add seismic demo subset and SeismicDataAdapter"
```

---

### Task 5: 把 IntentRouter / IdeaIntake / SeismicAdapter 接入 ScientistWorkflow

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py`
- Test: `backend/tests/test_workflow_intent_routing.py` (create)

**Interfaces:**
- Consumes: `IntentRouterAgent`, `IdeaIntakeAgent`, `SeismicDataAdapter` (from Tasks 2-4).
- Produces: `ScientistWorkflow._route_intent(run)` sets `run.intent` (router dict) and, for `idea_refinement`, `run.idea_brief`; `run()` runs it as the first `_step`. `_profile_scientific_data` branches on seismic domain to set `run.seismic_data_profile`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_workflow_intent_routing.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_workflow_intent_routing.py -v`
Expected: FAIL — `ScientistWorkflow` has no `intent_router`/`idea_intake` attrs or `_route_intent` method.

- [ ] **Step 3: Modify ScientistWorkflow**

In `backend/app/workflows/scientist_workflow.py`, add imports near the other agent imports (after `from app.agents.report_writer_agent import ReportWriterAgent`):

```python
from app.agents.idea_intake_agent import IdeaIntakeAgent
from app.agents.intent_router_agent import IntentRouterAgent
from app.tools.seismic_data import SeismicDataAdapter
```

In `ScientistWorkflow.__init__`, after `self.report_translator = ReportTranslatorAgent(self.llm)`:

```python
        self.intent_router = IntentRouterAgent(self.llm)
        self.idea_intake = IdeaIntakeAgent(self.llm)
        self.seismic_adapter = SeismicDataAdapter(settings.data_dir)
```

In `ScientistWorkflow.run`, insert the intent_router step before `await self._step(run, "planner", self._plan)`:

```python
            await self._step(run, "intent_router", self._route_intent)
            await self._step(run, "planner", self._plan)
```

Add the `_route_intent` method (place after `_plan`):

```python
    async def _route_intent(self, run: ResearchRun) -> None:
        run.intent = await self.intent_router.run(run)
        if run.mode == "idea_refinement":
            run.idea_brief = await self.idea_intake.run(run)
            run.steps[-1].summary = (
                f"Intent routed to idea_refinement (inferred={run.intent['mode']}, "
                f"confidence={run.intent['confidence']}); structured IdeaBrief ready."
            )
        else:
            run.steps[-1].summary = (
                f"Intent routed to {run.mode} (inferred={run.intent['mode']}, "
                f"confidence={run.intent['confidence']}); required_inputs={run.intent['required_inputs']}."
            )
```

Modify `_profile_scientific_data` to branch on seismic domain (replace the existing method body):

```python
    async def _profile_scientific_data(self, run: ResearchRun) -> None:
        if run.domain == "seismic_event_classification":
            run.seismic_data_profile = self.seismic_adapter.profile()
            run.data_profiles = []
            run.baseline_result_card = None
            run.steps[-1].summary = (
                f"Profiled seismic demo subset: {run.seismic_data_profile.num_events} events, "
                f"labels={run.seismic_data_profile.labels}; risks={len(run.seismic_data_profile.risks)}."
            )
            return
        run.data_profiles, run.baseline_result_card = self.scientific_data_agent.run()
        run.steps[-1].summary = (
            f"Profiled {len(run.data_profiles)} data sources and generated result card "
            f"{run.baseline_result_card.name if run.baseline_result_card else 'none'}."
        )
```

Add an `intent_router` entry to the `_stage_start_summary` dict (place it first):

```python
        "intent_router": "Classifying the research entry mode and structuring the user idea if present.",
        "planner": "Planning sub-questions, search queries, perspectives, evidence requirements, and risk controls.",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_workflow_intent_routing.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflows/scientist_workflow.py backend/tests/test_workflow_intent_routing.py
git commit -m "feat(v3-s1): wire IntentRouter/IdeaIntake/SeismicAdapter into ScientistWorkflow"
```

---

### Task 6: LangGraph intent_router 节点 + 三分支 placeholder

**Files:**
- Modify: `backend/app/workflows/langgraph_workflow.py`
- Modify: `backend/tests/test_langgraph_workflow.py`

**Interfaces:**
- Produces: `LangGraphWorkflow._build_graph` adds `intent_router` node (wraps inherited `_route_intent` via `_make_step_node`) + three passthrough branch nodes (`branch_discovery`/`branch_idea_refinement`/`branch_experiment_assistance`) + `add_conditional_edges("intent_router", _route_by_mode, {...})`. `_route_entry` fresh path returns `"intent_router"`. (`WorkflowState` is unchanged in S1 — `mode` already lives on `run`; `arena_result/iteration/debug_iteration/messages` channels are added in S3/S4 when nodes actually need them.)

- [ ] **Step 1: Write the failing test (extend existing langgraph test)**

In `backend/tests/test_langgraph_workflow.py`, update the `test_langgraph_workflow_completes_sync_run` step-name assertion (around line 131). Prepend `"intent_router"`:

```python
    step_names = [step.name for step in result.steps if step.status == "completed"]
    assert step_names == [
        "intent_router",
        "planner",
        "literature_search",
        "citation_verification",
        "evidence_ledger",
        "literature_mining",
        "scientific_data_profile",
        "hypothesis_debate",
        "experiment_design",
        "report_writer",
        "claim_verification",
        "report_revision",
        "claim_reverification",
        "report_translation",
    ]
```

Also update `test_langgraph_guided_workflow_pauses_for_citation_review` (around line 193):

```python
    completed = [step.name for step in first_pause.steps if step.status == "completed"]
    assert completed == ["intent_router", "planner", "literature_search", "citation_verification"]
```

Add a new test asserting the intent_router conditional edge routes by mode:

```python
@pytest.mark.asyncio
async def test_langgraph_intent_router_routes_by_mode(monkeypatch) -> None:
    workflow = _make_langgraph_workflow(monkeypatch)
    # _route_by_mode returns the run's mode, which maps to the matching branch node.
    discovery = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints(max_papers=1), mode="discovery")
    assert workflow._route_by_mode({"run": discovery}) == "discovery"
    refinement = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(max_papers=1), mode="idea_refinement")
    assert workflow._route_by_mode({"run": refinement}) == "idea_refinement"
    assistance = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(max_papers=1), mode="experiment_assistance")
    assert workflow._route_by_mode({"run": assistance}) == "experiment_assistance"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_langgraph_workflow.py -v`
Expected: FAIL — step_names assertion missing `intent_router`; `_route_by_mode` not defined.

- [ ] **Step 3: Modify LangGraphWorkflow**

In `backend/app/workflows/langgraph_workflow.py`, the `WorkflowState` TypedDict stays as-is in S1 (the run channel already carries `mode`; no new channel is needed yet).

In `_build_graph`, replace the `graph.add_edge(START, "entry")` + `_route_entry` conditional block. The current code is:

```python
        graph.add_edge(START, "entry")
        graph.add_conditional_edges(
            "entry",
            self._route_entry,
            {
                "planner": "planner",
                "evidence_ledger": "evidence_ledger",
                "scientific_data_profile": "scientific_data_profile",
            },
        )
```

Replace with (fresh runs route to intent_router; resume paths unchanged):

```python
        graph.add_edge(START, "entry")
        graph.add_conditional_edges(
            "entry",
            self._route_entry,
            {
                "intent_router": "intent_router",
                "evidence_ledger": "evidence_ledger",
                "scientific_data_profile": "scientific_data_profile",
            },
        )
        # v3 Layer 0: intent router branches to mode-specific placeholder nodes.
        # S3/S4/S6 replace these placeholders with Arena / Code Loop / Assistance.
        graph.add_node("intent_router", self._make_step_node("intent_router", "_route_intent"))
        graph.add_node("branch_discovery", self._node_passthrough)
        graph.add_node("branch_idea_refinement", self._node_passthrough)
        graph.add_node("branch_experiment_assistance", self._node_passthrough)
        graph.add_conditional_edges(
            "intent_router",
            self._route_by_mode,
            {
                "discovery": "branch_discovery",
                "idea_refinement": "branch_idea_refinement",
                "experiment_assistance": "branch_experiment_assistance",
            },
        )
        graph.add_edge("branch_discovery", "planner")
        graph.add_edge("branch_idea_refinement", "planner")
        graph.add_edge("branch_experiment_assistance", "planner")
```

Update `_route_entry` so the fresh path returns `"intent_router"` instead of `"planner"`:

```python
    def _route_entry(self, state: WorkflowState) -> str:
        run = state["run"]
        if run.current_stage == "awaiting_citation_review":
            return "evidence_ledger"
        if run.current_stage == "awaiting_evidence_review":
            return "scientific_data_profile"
        return "intent_router"
```

Add the two new methods (place near `_node_entry`):

```python
    async def _node_passthrough(self, state: WorkflowState) -> WorkflowState:
        """Placeholder for a mode-specific branch; S3/S4/S6 fill these in."""
        return {"run": state["run"]}

    def _route_by_mode(self, state: WorkflowState) -> str:
        return state["run"].mode
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_langgraph_workflow.py -v`
Expected: PASS (all langgraph tests, including updated step-name assertions and the new `_route_by_mode` test).

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflows/langgraph_workflow.py backend/tests/test_langgraph_workflow.py
git commit -m "feat(v3-s1): add LangGraph intent_router conditional edge with mode branches"
```

---

### Task 7: API 透传 mode + 前端接通

**Files:**
- Modify: `backend/app/api/routes_runs.py`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/workbench/Workbench.tsx`
- Test: `backend/tests/test_api_routes.py` (extend)

**Interfaces:**
- Produces: `POST /api/runs` accepts `mode` in body and stores it on the created `ResearchRun`. Frontend `createRun(question, domain, maxPapers, enableSemanticScholar, enableArxiv, workflowMode, mode)` sends `mode`. `ResearchRun` TS type gains `mode`, `idea_brief`, `seismic_data_profile`.

- [ ] **Step 1: Write the failing backend test**

`backend/tests/test_api_routes.py` already has a module-level `client = TestClient(app)` (line 17). Append this test at the end of the file (it reuses that `client`):

```python
def test_create_run_carries_mode() -> None:
    response = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q", "mode": "idea_refinement"},
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "idea_refinement"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_api_routes.py::test_create_run_carries_mode -v`
Expected: FAIL — `response.json()` has no `mode` key (KeyError) because `create_run` does not pass `mode`.

- [ ] **Step 3: Modify the backend route**

In `backend/app/api/routes_runs.py`, update `create_run` (line ~36) to pass `mode`:

```python
@router.post("", response_model=ResearchRun)
async def create_run(payload: ResearchRunCreate) -> ResearchRun:
    run = ResearchRun(
        domain=payload.domain,
        question=payload.question,
        constraints=payload.constraints,
        mode=payload.mode,
    )
    _write_workspace(run)
    return run_store.create(run)
```

- [ ] **Step 4: Run backend test to verify it passes**

Run: `cd backend && python -m pytest tests/test_api_routes.py::test_create_run_carries_mode -v`
Expected: PASS

- [ ] **Step 5: Modify the frontend api client**

In `frontend/lib/api.ts`, extend the `ResearchRun` type (add three fields after `question: string;`):

```typescript
  mode: "discovery" | "idea_refinement" | "experiment_assistance";
  idea_brief?: {
    research_problem: string;
    user_idea?: string;
    target_task: string;
    input_data: string[];
    proposed_method?: string;
    expected_contribution?: string;
    target_labels: string[];
    unknowns: string[];
    risks: string[];
  };
  seismic_data_profile?: {
    dataset_name: string;
    num_events: number;
    labels: Record<string, number>;
    channels: string[];
    sampling_rate?: number;
    window_seconds?: number;
    split_strategy: string;
    risks: string[];
    source_path?: string;
  };
```

Update `createRun` signature and body (add `mode` param, send it):

```typescript
export async function createRun(
  question: string,
  domain: string,
  maxPapers: number,
  enableSemanticScholar: boolean,
  enableArxiv: boolean,
  workflowMode: "auto" | "guided" = "auto",
  mode: "discovery" | "idea_refinement" | "experiment_assistance" = "discovery"
) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs`, {
    method: "POST",
    body: JSON.stringify({
      domain,
      question,
      mode,
      constraints: {
        must_verify_citations: true,
        max_papers: maxPapers,
        require_experiment_plan: true,
        enable_browser_worker: false,
        enable_semantic_scholar: enableSemanticScholar,
        enable_arxiv: enableArxiv,
        workflow_mode: workflowMode
      }
    })
  });
}
```

- [ ] **Step 6: Modify Workbench handleStart**

In `frontend/components/workbench/Workbench.tsx`, update the `createRun` call inside `handleStart` (around line 204) to pass `draft.researchMode`:

```typescript
      const created = await createRun(
        draft.question,
        draft.domain,
        draft.maxPapers,
        draft.enableSemanticScholar,
        draft.enableArxiv,
        draft.workflowMode,
        draft.researchMode
      );
```

- [ ] **Step 7: Manual frontend verification**

Run the frontend dev server and verify the wiring:

```bash
cd frontend && npm run dev
```

Manual checks:
1. Open http://localhost:3000, choose **Seismic Expert** → **创意精修**, enter the seismic default question, click 启动.
2. After the run starts, refresh and open the run; `run.mode` should be `"idea_refinement"` and (once intent_router completes) `run.idea_brief` populated.
3. Choose **发现** instead; `run.mode` should be `"discovery"` and `idea_brief` absent.
4. Confirm v1/v2 Classic Workflow still launches and completes (no regression).

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes_runs.py backend/tests/test_api_routes.py frontend/lib/api.ts frontend/components/workbench/Workbench.tsx
git commit -m "feat(v3-s1): thread mode through POST /api/runs and frontend Mode Selector"
```

---

## S1 验收（全量回归）

- [ ] **Step 9: Run the full backend test suite**

```bash
cd backend && python -m pytest -q
```

Expected: all green, including:
- new tests: `test_v3_schemas`, `test_intent_router_agent`, `test_idea_intake_agent`, `test_seismic_data_adapter`, `test_workflow_intent_routing`, `test_langgraph_intent_router_routes_by_mode`, `test_create_run_carries_mode`.
- updated tests: `test_langgraph_workflow_completes_sync_run`, `test_langgraph_guided_workflow_pauses_for_citation_review` (now include `intent_router`).
- v1/v2 regression: `test_classic_workflow_still_completes`, `test_workflow_mock`, `test_planner_langchain`, existing `test_api_routes` tests.

- [ ] **Step 10: S1 acceptance criteria check**

Verify against the S1 spec in `prd_v3_sprint.md`:
1. 三模式可路由到不同分支节点 — `test_langgraph_intent_router_routes_by_mode` ✓
2. 地震问题生成结构化 `IdeaBrief` — `test_route_intent_sets_intent_and_idea_brief_for_refinement` ✓
3. v1/v2 tests 不破 — Step 9 全绿 ✓

- [ ] **Step 11: Final commit (if any stray changes)**

```bash
git add -A
git status
# only commit if there are leftover related changes
git commit -m "chore(v3-s1): s1 acceptance regression green"
```

## 已知 S1 局限（后续 Sprint 处理）

- 三个分支节点目前都是 passthrough，所有模式仍走 v1/v2 线性链到报告。地震 run 的最终报告仍是材料风格占位（S3 Arena / S4 Code Loop / S6 Experiment Assistance 接入后替换）。
- `WorkflowState` 本 Sprint 不新增 channel（`mode` 已在 `run` 上；`arena_result/iteration/debug_iteration/messages` 等到 S3/S4 节点真正需要时再加）。
- 前端只把 `mode` 透传到后端；**按 mode 切换独立输入框**（direction / idea / data_path+code_path）推迟到 S6（spec S6 已列「前端三模式 input 差异化落地」）。S1 的 question 文本框对三种模式通用，IdeaIntake 用 `run.question` 作 `user_idea` 兜底。
- IntentRouter 当前以审计/展示为主（前端 Mode Selector 已显式选 mode，路由不自动覆盖用户选择）。
- 地震 baseline result card 暂为 None（S4 生成真实实验 result card）。
