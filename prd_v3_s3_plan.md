# v3 Sprint S3 实施计划：Hypothesis Arena 竞技 + Baseline 自动化

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 v1/v2 线性的"生成→批判→修订"假设链升级为 v3 竞技式 Arena（Discovery 排名竞技 / Idea Refinement 消融式），多视角 Critic 并行 + 加权排名 + 自动选 Top1（无人工 gate）；同时把 S2 的按需 baseline 发现/验证改成**自动 graph 节点**，并新增"从论文摘要 + PDF 正文挖 github 链接"通道，让"论文→代码对应"更准。

**Architecture:** Arena 用 3 个视角 Critic（Domain Scientist / ML-Experiment / Skeptical Reviewer）**并行** LCEL 链（asyncio.gather），每个对全部候选在 8 维打分，加权汇总排名。Discovery 模式：生成 N 假设→3 视角并行批判→排名→Top1/Top2→Revision→自动选 Top1。Idea Refinement 模式：H_main（来自 IdeaBrief）+ 3 消融挑战者→批判→输出 ablation_design。baseline 自动化：新增 `extract_code_urls`（摘要 regex + PDF 正文 regex，top-N）→ 填 `paper.code_url`；BaselineDiscoveryAgent 优先用论文自声明 code_url（高精度），GitHub 标题搜兜底；RepositoryVerifier 自动验证 top-N 候选。Arena + baseline 作为 **seismic 专属 graph 节点**插入（替换 seismic 的线性 hypothesis_debate），非 seismic 保持 v1/v2 线性不变。

**Tech Stack:** Python 3.11 / FastAPI / Pydantic / LangChain LCEL / LangGraph StateGraph / httpx / pypdf / pytest / Next.js。

## Global Constraints

- 新 LLM agent（CriticArenaAgent / HypothesisArenaAgent / ChallengerAgent）走 `LLMClientRunnable` 适配器（`build_agent_prompt` 保留 system prompt 字面花括号），`agent` 字段分别为 `critic_arena` / `hypothesis_arena` / `challenger`，malformed 输出落 fallback 不崩。
- 3 视角 Critic 必须**并行**（`asyncio.gather`），不是串行 3 次调用。
- **不破坏 v1/v2 classic**：Arena + baseline-auto 节点只对 `run.domain == "seismic_event_classification"` 生效；非 seismic 的 `hypothesis_debate` 线性链（`_generate_and_critique`）保持不变，相关测试不破。
- **无人工 gate**：Arena 自动选 Top1（`selected=True`），不调 `_pause_for_human`、不 `interrupt()`。Switchback 的人工确认推迟到 S5（且 S5 也按用户要求做成自动）。
- code_url 提取：摘要 regex（所有论文，便宜）+ PDF 正文 regex（仅 top-N=5 篇、且 `paper.pdf_url` 存在才下载解析）；regex 只认 `github.com/owner/repo` 形态；下载/解析失败优雅降级（不影响 run）。
- BaselineDiscoveryAgent 优先用 `paper.code_url`（`code_source="paper_abstract"` / `"paper_pdf"`，`verified_repo` 初始 True，因为是论文自声明）；无 code_url 的论文才走 GitHub 标题搜（`code_source="github_search"`）。
- RepositoryVerifier 自动只验证 top-N（按 stars 降序前 3）候选，避免一个 run 对 15 个候选都调 Qwen+GitHub（时间+rate limit）。
- `arena_level="simplified_ranking"`；Elo 相关字段（`elo_rating`/`pairwise_results`/`evolution_history`）预留 null，Elo 升级推迟 S7。
- 不 commit（用户偏好）。后端测试在 Docker dev 栈：`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest <path> -v`。
- 文件路径相对仓库根 `d:/For work/TrustSci-Agent/`。

## File Structure

- **Create** `backend/app/schemas/arena.py` — `HypothesisArenaResult` / `HypothesisArenaCandidate` / `AblationChallenge`。
- **Create** `backend/app/agents/critic_arena_agent.py` — 3 视角并行 Critic。
- **Create** `backend/app/agents/hypothesis_arena_agent.py` — Discovery 排名 + Idea Refinement 消融式。
- **Create** `backend/app/agents/challenger_agent.py` — Idea Refinement 的消融挑战者生成。
- **Create** `backend/app/tools/code_url_extractor.py` — 摘要 + PDF 正文挖 github 链接。
- **Create** `backend/tests/test_arena_schemas.py`
- **Create** `backend/tests/test_critic_arena_agent.py`
- **Create** `backend/tests/test_hypothesis_arena_agent.py`
- **Create** `backend/tests/test_challenger_agent.py`
- **Create** `backend/tests/test_code_url_extractor.py`
- **Create** `backend/tests/test_arena_workflow_integration.py`
- **Create** `frontend/components/workbench/HypothesisArenaPanel.tsx`
- **Modify** `backend/app/schemas/run.py` — 加 `arena_result: HypothesisArenaResult | None`。
- **Modify** `backend/app/agents/baseline_discovery_agent.py` — 优先用 `paper.code_url`。
- **Modify** `backend/app/workflows/scientist_workflow.py` — 加 `_run_arena` / `_extract_code_urls` / `_discover_baselines_auto` / `_verify_baselines_auto` 方法；`_run_after_evidence_review` 对 seismic 走 Arena+baseline 分支。
- **Modify** `backend/app/workflows/langgraph_workflow.py` — seismic 的 `hypothesis_debate` 替换为 arena + baseline 节点链（条件边按 domain 分流）。
- **Modify** `frontend/lib/api.ts` — `ResearchRun` 类型加 `arena_result`。
- **Modify** `frontend/components/workbench/Workbench.tsx` — seismic 工作区加 `HypothesisArenaPanel`。

---

### Task 1: Arena schema + ResearchRun.arena_result

**Files:**
- Create: `backend/app/schemas/arena.py`
- Modify: `backend/app/schemas/run.py`
- Test: `backend/tests/test_arena_schemas.py`

**Interfaces:**
- Produces: `HypothesisArenaCandidate`（`hypothesis_id, statement, is_user_idea, critic_scores: dict[str, CriticReview], weighted_score: float, rank: int`）、`AblationChallenge`（`challenge_id, tests_innovation_point, expected_insight, derivation_from_main`）、`HypothesisArenaResult`（`arena_id, mode, arena_level, candidates, ranking, selected_for_experiment, switchback_candidate, ablation_design`）。`ResearchRun.arena_result: HypothesisArenaResult | None`。
- Consumes: `app.schemas.hypothesis.CriticReview`（已有 8 维）。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_arena_schemas.py
from app.schemas.arena import AblationChallenge, HypothesisArenaCandidate, HypothesisArenaResult
from app.schemas.hypothesis import CriticReview
from app.schemas.run import ResearchConstraints, ResearchRun


def _review(score: int = 8) -> CriticReview:
    return CriticReview(novelty=score, self_consistency=score, verifiability=score,
                        data_availability=score, feasibility=score, evidence_support=score,
                        reproducibility=score, competition_fit=score, risk="r", revision_advice="a")


def test_arena_candidate_defaults() -> None:
    c = HypothesisArenaCandidate(hypothesis_id="H1", statement="s", is_user_idea=False,
                                 critic_scores={"domain_scientist": _review()}, weighted_score=80.0, rank=1)
    assert c.rank == 1
    assert c.critic_scores["domain_scientist"].novelty == 8


def test_arena_result_defaults() -> None:
    r = HypothesisArenaResult(arena_id="a1", mode="discovery", arena_level="simplified_ranking",
                              candidates=[], ranking=[], selected_for_experiment="",
                              switchback_candidate=None, ablation_design=[])
    assert r.arena_level == "simplified_ranking"
    assert r.switchback_candidate is None


def test_research_run_arena_field() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints())
    assert run.arena_result is None


def test_ablation_challenge() -> None:
    a = AblationChallenge(challenge_id="H_c1", tests_innovation_point="spectrogram branch",
                          expected_insight="verify fusion > waveform-only", derivation_from_main="remove spectrogram")
    assert a.tests_innovation_point == "spectrogram branch"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_arena_schemas.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'app.schemas.arena'`

- [ ] **Step 3: Write the schema**

```python
# backend/app/schemas/arena.py
from pydantic import BaseModel, Field

from app.schemas.hypothesis import CriticReview


class HypothesisArenaCandidate(BaseModel):
    hypothesis_id: str
    statement: str
    is_user_idea: bool = False
    critic_scores: dict[str, CriticReview] = Field(default_factory=dict)
    weighted_score: float = 0.0
    rank: int = 0


class AblationChallenge(BaseModel):
    challenge_id: str
    tests_innovation_point: str
    expected_insight: str
    derivation_from_main: str


class HypothesisArenaResult(BaseModel):
    arena_id: str
    mode: str  # discovery | idea_refinement
    arena_level: str = "simplified_ranking"  # elo_tournament deferred to S7
    candidates: list[HypothesisArenaCandidate] = Field(default_factory=list)
    ranking: list[str] = Field(default_factory=list)  # hypothesis_id by rank
    selected_for_experiment: str = ""
    switchback_candidate: str | None = None
    ablation_design: list[AblationChallenge] = Field(default_factory=list)
    # Elo upgrade fields (S7) — reserved, unused in S3:
    pairwise_results: list[dict] | None = None
    evolution_history: list[dict] | None = None
```

In `backend/app/schemas/run.py`, add import (after `from app.schemas.baseline import BaselineCandidate`):

```python
from app.schemas.arena import HypothesisArenaResult
```

Add field to `ResearchRun` (after `novelty_report`):

```python
    arena_result: HypothesisArenaResult | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_arena_schemas.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 2: CriticArenaAgent（3 视角并行）

**Files:**
- Create: `backend/app/agents/critic_arena_agent.py`
- Test: `backend/tests/test_critic_arena_agent.py`

**Interfaces:**
- Consumes: `LLMClient`、`list[Hypothesis]`、`list[EvidenceItem]`。
- Produces: `CriticArenaAgent.arun(hypotheses, evidence, *, run_id) -> dict[str, dict[str, CriticReview]]`：外层 key = perspective（`domain_scientist` / `ml_critic` / `skeptical_reviewer`），内层 key = `hypothesis_id`，值 = `CriticReview`（8 维）。3 视角**并行**（asyncio.gather）。fallback：每个视角用确定性默认评分。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_critic_arena_agent.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_critic_arena_agent.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/critic_arena_agent.py
import asyncio
import json

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import CriticReview, Hypothesis

PERSPECTIVES = ("domain_scientist", "ml_critic", "skeptical_reviewer")

_PERSPECTIVE_PROMPTS = {
    "domain_scientist": "You are the Domain Scientist Critic. Score each hypothesis on scientific value, mechanism soundness, and domain novelty.",
    "ml_critic": "You are the ML/Experiment Critic. Score each hypothesis on data availability, feasibility, reproducibility, and verification path clarity.",
    "skeptical_reviewer": "You are the Skeptical Reviewer. Score each hypothesis on self-consistency, evidence support, and risk of overclaiming.",
}

_SYSTEM_TAIL = """

Score EVERY provided hypothesis on these 8 dimensions (integers 1..10): novelty, self_consistency, verifiability, data_availability, feasibility, evidence_support, reproducibility, competition_fit.
Return JSON only: {"reviews": [{"hypothesis_id": "...", "novelty": N, "self_consistency": N, "verifiability": N, "data_availability": N, "feasibility": N, "evidence_support": N, "reproducibility": N, "competition_fit": N, "risk": "...", "revision_advice": "..."}]}.
Do not invent citations or evidence ids."""


class CriticArenaAgent:
    """3-perspective parallel critic. Each perspective is an independent LCEL
    chain scoring all hypotheses on 8 dimensions. Runs concurrently via gather."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(self, hypotheses: list[Hypothesis], evidence: list[EvidenceItem], *, run_id: str) -> dict[str, dict[str, CriticReview]]:
        async def _one(perspective: str) -> dict[str, CriticReview]:
            return await self._run_perspective(perspective, hypotheses, evidence, run_id)
        results = await asyncio.gather(*[_one(p) for p in PERSPECTIVES])
        return dict(zip(PERSPECTIVES, results))

    async def _run_perspective(self, perspective: str, hypotheses: list[Hypothesis], evidence: list[EvidenceItem], run_id: str) -> dict[str, CriticReview]:
        fallback = {h.hypothesis_id: _fallback_review(h, perspective) for h in hypotheses}
        if self.llm is None:
            return fallback
        system = _PERSPECTIVE_PROMPTS[perspective] + _SYSTEM_TAIL
        prompt = build_agent_prompt(system)
        chain = (
            prompt
            | LLMClientRunnable(self.llm).bind(fallback={"reviews": []}, run_id=run_id, agent="critic_arena")
            | FallbackParser(lambda content: _normalize(content, hypotheses, fallback), fallback)
        )
        return await chain.ainvoke({"user_prompt": _build_user_prompt(hypotheses, evidence)})


def _build_user_prompt(hypotheses: list[Hypothesis], evidence: list[EvidenceItem]) -> str:
    payload = {
        "hypotheses": [{"hypothesis_id": h.hypothesis_id, "statement": h.statement, "rationale": h.rationale,
                         "verification_path": h.verification_path, "novelty_claim": h.novelty_claim,
                         "supporting_evidence": h.supporting_evidence} for h in hypotheses],
        "evidence": [{"evidence_id": e.evidence_id, "claim": e.claim, "verified": e.verified} for e in evidence[:16]],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize(content: object, hypotheses: list[Hypothesis], fallback: dict[str, CriticReview]) -> dict[str, CriticReview]:
    if not isinstance(content, dict) or not isinstance(content.get("reviews"), list):
        return fallback
    by_id = {str(r.get("hypothesis_id")): r for r in content["reviews"] if isinstance(r, dict) and r.get("hypothesis_id")}
    out: dict[str, CriticReview] = {}
    for h in hypotheses:
        raw = by_id.get(h.hypothesis_id)
        if not isinstance(raw, dict):
            out[h.hypothesis_id] = fallback[h.hypothesis_id]
            continue
        try:
            out[h.hypothesis_id] = CriticReview(
                novelty=_score(raw.get("novelty")), self_consistency=_score(raw.get("self_consistency")),
                verifiability=_score(raw.get("verifiability")), data_availability=_score(raw.get("data_availability")),
                feasibility=_score(raw.get("feasibility")), evidence_support=_score(raw.get("evidence_support")),
                reproducibility=_score(raw.get("reproducibility")), competition_fit=_score(raw.get("competition_fit")),
                risk=str(raw.get("risk") or "risk noted"), revision_advice=str(raw.get("revision_advice") or "revise bounds"),
            )
        except Exception:
            out[h.hypothesis_id] = fallback[h.hypothesis_id]
    # Ensure every hypothesis is covered; missing -> fallback.
    for h in hypotheses:
        out.setdefault(h.hypothesis_id, fallback[h.hypothesis_id])
    return out


def _fallback_review(hypothesis: Hypothesis, perspective: str) -> CriticReview:
    base = 8 if perspective != "skeptical_reviewer" else 6
    has_ev = 7 if hypothesis.supporting_evidence else 5
    return CriticReview(novelty=base, self_consistency=base, verifiability=base, data_availability=base - 1,
                        feasibility=base, evidence_support=has_ev, reproducibility=base - 1, competition_fit=base - 1,
                        risk="Deterministic fallback: evidence or feasibility risk requires revision.",
                        revision_advice="Bound novelty and tie to a concrete dataset/baseline.")


def _score(value: object) -> int:
    try:
        return max(1, min(10, int(float(value))))
    except (TypeError, ValueError):
        return 7
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_critic_arena_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 3: ChallengerAgent（Idea Refinement 消融挑战者）

**Files:**
- Create: `backend/app/agents/challenger_agent.py`
- Test: `backend/tests/test_challenger_agent.py`

**Interfaces:**
- Consumes: `LLMClient`、`IdeaBrief`、`Hypothesis`（H_main）。
- Produces: `ChallengerAgent.arun(h_main, idea_brief, *, run_id) -> tuple[list[Hypothesis], list[AblationChallenge]]`：3 个消融挑战者（去掉/替换 H_main 的创新点）+ 对应 ablation_design。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_challenger_agent.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_challenger_agent.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/challenger_agent.py
import json

from app.llm.interface import LLMClient
from app.llm.langchain_adapter import FallbackParser, LLMClientRunnable, build_agent_prompt
from app.schemas.arena import AblationChallenge
from app.schemas.hypothesis import Hypothesis
from app.schemas.idea import IdeaBrief

SYSTEM_PROMPT = """You are the Challenger Agent for TrustSci-Agent v3 (Idea Refinement ablation arena).
Given the user's main hypothesis (H_main) and idea brief, generate exactly 3 ablation challengers.
Each challenger removes or replaces ONE innovation point of H_main, to test whether that innovation point truly contributes.
Return JSON only: {"challenges": [{"challenge_id": "H_c1", "hypothesis_id": "H_c1", "statement": "...", "rationale": "...", "novelty_claim": "...", "verification_path": "...", "tests_innovation_point": "...", "expected_insight": "...", "derivation_from_main": "..."}]}.
Do not invent citations or datasets."""


class ChallengerAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    async def arun(self, h_main: Hypothesis, idea_brief: IdeaBrief, *, run_id: str) -> tuple[list[Hypothesis], list[AblationChallenge]]:
        fallback = _fallback_challenges(h_main, idea_brief)
        if self.llm is None:
            return _split(fallback)
        chain = (
            build_agent_prompt(SYSTEM_PROMPT)
            | LLMClientRunnable(self.llm).bind(fallback={"challenges": []}, run_id=run_id, agent="challenger")
            | FallbackParser(lambda content: _normalize(content, h_main, fallback), fallback)
        )
        normalized = await chain.ainvoke({"user_prompt": _build_user_prompt(h_main, idea_brief)})
        return _split(normalized)


def _build_user_prompt(h_main: Hypothesis, idea_brief: IdeaBrief) -> str:
    payload = {
        "h_main": {"hypothesis_id": h_main.hypothesis_id, "statement": h_main.statement,
                   "rationale": h_main.rationale, "verification_path": h_main.verification_path,
                   "novelty_claim": h_main.novelty_claim},
        "idea_brief": {"user_idea": idea_brief.user_idea, "target_task": idea_brief.target_task,
                       "input_data": idea_brief.input_data, "target_labels": idea_brief.target_labels},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize(content: object, h_main: Hypothesis, fallback: list[dict]) -> list[dict]:
    if not isinstance(content, dict) or not isinstance(content.get("challenges"), list):
        return fallback
    out: list[dict] = []
    for raw in content["challenges"][:3]:
        if not isinstance(raw, dict):
            continue
        cid = str(raw.get("challenge_id") or raw.get("hypothesis_id") or "").strip()
        statement = str(raw.get("statement") or "").strip()
        if not cid or not statement:
            continue
        out.append({
            "challenge_id": cid, "hypothesis_id": cid, "statement": statement,
            "rationale": str(raw.get("rationale") or "ablation of an innovation point"),
            "novelty_claim": str(raw.get("novelty_claim") or "reduced variant"),
            "verification_path": str(raw.get("verification_path") or "compare against H_main"),
            "tests_innovation_point": str(raw.get("tests_innovation_point") or "an innovation point"),
            "expected_insight": str(raw.get("expected_insight") or "whether the innovation point contributes"),
            "derivation_from_main": str(raw.get("derivation_from_main") or "remove/replace an innovation point"),
        })
    return out or fallback


def _fallback_challenges(h_main: Hypothesis, idea_brief: IdeaBrief) -> list[dict]:
    inputs = idea_brief.input_data or ["waveform", "spectrogram"]
    variants = [
        ("H_c1", f"{h_main.statement} (waveform-only ablation)", "waveform branch",
         "whether waveform channel contributes", "remove non-waveform inputs"),
        ("H_c2", f"{h_main.statement} (single-representation ablation)", "multi-representation fusion",
         "whether fusion beats single representation", f"keep only {inputs[0] if inputs else 'one input'}"),
        ("H_c3", f"{h_main.statement} (simple-concat ablation)", "fusion module",
         "whether the fusion module beats simple concat", "replace fusion module with concatenation"),
    ]
    return [{
        "challenge_id": cid, "hypothesis_id": cid, "statement": stmt,
        "rationale": "ablation challenger to test an innovation point of H_main",
        "novelty_claim": "reduced variant of H_main", "verification_path": "compare against H_main",
        "tests_innovation_point": tip, "expected_insight": ei, "derivation_from_main": deriv,
    } for cid, stmt, tip, ei, deriv in variants]


def _split(challenges: list[dict]) -> tuple[list[Hypothesis], list[AblationChallenge]]:
    hyps = [Hypothesis(hypothesis_id=c["hypothesis_id"], statement=c["statement"], rationale=c["rationale"],
                       novelty_claim=c["novelty_claim"], verification_path=c["verification_path"]) for c in challenges]
    design = [AblationChallenge(challenge_id=c["challenge_id"], tests_innovation_point=c["tests_innovation_point"],
                                expected_insight=c["expected_insight"], derivation_from_main=c["derivation_from_main"]) for c in challenges]
    return hyps, design
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_challenger_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 4: HypothesisArenaAgent（Discovery 排名 + Idea Refinement 消融式）

**Files:**
- Create: `backend/app/agents/hypothesis_arena_agent.py`
- Test: `backend/tests/test_hypothesis_arena_agent.py`

**Interfaces:**
- Consumes: `HypothesisAgent`、`CriticArenaAgent`、`ChallengerAgent`、`RevisionAgent`、`GapFinderAgent`、`IdeaIntakeAgent`、`list[EvidenceItem]`、`list[DatasetProfile]`、`IdeaBrief | None`、`list[Paper]`、`mode`。
- Produces: `HypothesisArenaAgent.arun(mode, gaps, evidence, data_profiles, idea_brief, papers, *, run_id) -> tuple[HypothesisArenaResult, list[Hypothesis]]`。Discovery：生成 N→3 视角并行批判→加权排名→Top1/Top2→Revision→自动选 Top1。Idea Refinement：H_main + 3 挑战者→批判→ablation_design→选 H_main。返回的 `list[Hypothesis]` 带 `selected` 标记，供下游 experiment_design 用。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_hypothesis_arena_agent.py
import pytest

from app.agents.hypothesis_arena_agent import HypothesisArenaAgent, ARENA_WEIGHTS
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import Hypothesis


class StubHypothesisAgent:
    async def arun(self, gaps, evidence, data_profiles, *, run_id):
        return [Hypothesis(hypothesis_id="H1", statement="s1", rationale="r", novelty_claim="n", verification_path="v"),
                Hypothesis(hypothesis_id="H2", statement="s2", rationale="r", novelty_claim="n", verification_path="v"),
                Hypothesis(hypothesis_id="H3", statement="s3", rationale="r", novelty_claim="n", verification_path="v")]


class StubCriticArena:
    async def arun(self, hypotheses, evidence, *, run_id):
        # H1 scores high, H3 second, H2 low
        from app.schemas.hypothesis import CriticReview
        high = CriticReview(novelty=9, self_consistency=9, verifiability=9, data_availability=9, feasibility=9,
                            evidence_support=9, reproducibility=9, competition_fit=9, risk="r", revision_advice="a")
        low = CriticReview(novelty=5, self_consistency=5, verifiability=5, data_availability=5, feasibility=5,
                           evidence_support=5, reproducibility=5, competition_fit=5, risk="r", revision_advice="a")
        mid = CriticReview(novelty=7, self_consistency=7, verifiability=7, data_availability=7, feasibility=7,
                           evidence_support=7, reproducibility=7, competition_fit=7, risk="r", revision_advice="a")
        per = {"domain_scientist": {"H1": high, "H2": low, "H3": mid},
               "ml_critic": {"H1": high, "H2": low, "H3": mid},
               "skeptical_reviewer": {"H1": high, "H2": low, "H3": mid}}
        return per


class StubRevision:
    def run(self, hypotheses):
        for h in hypotheses:
            h.revised_statement = h.statement + " (revised)"
        return hypotheses


@pytest.mark.asyncio
async def test_discovery_arena_ranks_and_selects_top1() -> None:
    agent = HypothesisArenaAgent(hypothesis_agent=StubHypothesisAgent(), critic_arena=StubCriticArena(), revision=StubRevision())
    result, hypotheses = await agent.arun("discovery", gaps=[], evidence=[], data_profiles=[], idea_brief=None, papers=[], run_id="run_x")
    assert result.mode == "discovery"
    assert result.ranking[0] == "H1"  # highest weighted score
    assert result.selected_for_experiment == "H1"
    assert result.switchback_candidate == "H3"  # second rank
    selected = [h for h in hypotheses if h.selected]
    assert len(selected) == 1 and selected[0].hypothesis_id == "H1"


@pytest.mark.asyncio
async def test_arena_weighted_score_is_normalized_0_to_100() -> None:
    from app.schemas.hypothesis import CriticReview
    perfect = CriticReview(novelty=10, self_consistency=10, verifiability=10, data_availability=10, feasibility=10,
                           evidence_support=10, reproducibility=10, competition_fit=10, risk="r", revision_advice="a")
    scores = {p: {"H1": perfect} for p in ("domain_scientist", "ml_critic", "skeptical_reviewer")}
    score = HypothesisArenaAgent(hypothesis_agent=StubHypothesisAgent(), critic_arena=StubCriticArena(), revision=StubRevision())._weighted_score(scores, "H1")
    assert 99.0 <= score <= 100.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_hypothesis_arena_agent.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Write the agent**

```python
# backend/app/agents/hypothesis_arena_agent.py
from app.agents.critic_arena_agent import CriticArenaAgent, PERSPECTIVES
from app.agents.hypothesis_agent import HypothesisAgent
from app.agents.revision_agent import RevisionAgent
from app.schemas.arena import AblationChallenge, HypothesisArenaCandidate, HypothesisArenaResult
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import CriticReview, Hypothesis

ARENA_WEIGHTS = {
    "novelty": 1.5, "verifiability": 1.5, "reproducibility": 1.3, "evidence_support": 1.3,
    "feasibility": 1.2, "data_availability": 1.2, "competition_fit": 1.0, "self_consistency": 1.0,
}
_DIMS = ("novelty", "self_consistency", "verifiability", "data_availability", "feasibility",
         "evidence_support", "reproducibility", "competition_fit")
_WEIGHT_SUM = sum(ARENA_WEIGHTS.values())


class HypothesisArenaAgent:
    """v3 Hypothesis Arena: Discovery ranking or Idea Refinement ablation.

    Discovery: generate N -> 3 parallel critics -> weighted rank -> Top1/Top2 -> revision -> auto-select Top1.
    Idea Refinement: H_main + 3 challengers -> critics -> ablation_design -> select H_main.
    No human gate (auto-select).
    """

    def __init__(self, *, hypothesis_agent: HypothesisAgent, critic_arena: CriticArenaAgent,
                 revision: RevisionAgent, challenger=None) -> None:
        self.hypothesis_agent = hypothesis_agent
        self.critic_arena = critic_arena
        self.revision = revision
        self.challenger = challenger

    async def arun(self, mode, gaps, evidence: list[EvidenceItem], data_profiles, idea_brief, papers, *, run_id: str) -> tuple[HypothesisArenaResult, list[Hypothesis]]:
        if mode == "idea_refinement":
            return await self._idea_refinement(evidence, idea_brief, run_id)
        return await self._discovery(gaps, evidence, data_profiles, run_id)

    async def _discovery(self, gaps, evidence, data_profiles, run_id) -> tuple[HypothesisArenaResult, list[Hypothesis]]:
        hypotheses = await self.hypothesis_agent.arun(gaps, evidence, data_profiles, run_id=run_id)
        scores = await self.critic_arena.arun(hypotheses, evidence, run_id=run_id)
        ranked = self._rank(hypotheses, scores)
        top1, top2 = ranked[0], (ranked[1] if len(ranked) > 1 else None)
        # Revise top candidates only (cost control).
        self.revision.run([top1] + ([top2] if top2 else []))
        for h in hypotheses:
            h.selected = (h.hypothesis_id == top1.hypothesis_id)
        candidates = self._candidates(hypotheses, scores, ranked)
        result = HypothesisArenaResult(
            arena_id=f"arena_{run_id[:12]}", mode="discovery", arena_level="simplified_ranking",
            candidates=candidates, ranking=[c.hypothesis_id for c in candidates],
            selected_for_experiment=top1.hypothesis_id,
            switchback_candidate=top2.hypothesis_id if top2 else None, ablation_design=[],
        )
        return result, hypotheses

    async def _idea_refinement(self, evidence, idea_brief, run_id) -> tuple[HypothesisArenaResult, list[Hypothesis]]:
        h_main = self._h_main_from_idea(idea_brief)
        challengers: list[Hypothesis] = []
        ablation: list[AblationChallenge] = []
        if self.challenger is not None and idea_brief is not None:
            challengers, ablation = await self.challenger.arun(h_main, idea_brief, run_id=run_id)
        all_hyps = [h_main] + challengers
        scores = await self.critic_arena.arun(all_hyps, evidence, run_id=run_id)
        ranked = self._rank(all_hyps, scores)
        self.revision.run([h_main])
        for h in all_hyps:
            h.selected = (h.hypothesis_id == h_main.hypothesis_id)
        candidates = self._candidates(all_hyps, scores, ranked)
        # mark which is the user idea
        for c in candidates:
            c.is_user_idea = (c.hypothesis_id == h_main.hypothesis_id)
        result = HypothesisArenaResult(
            arena_id=f"arena_{run_id[:12]}", mode="idea_refinement", arena_level="simplified_ranking",
            candidates=candidates, ranking=[c.hypothesis_id for c in candidates],
            selected_for_experiment=h_main.hypothesis_id, switchback_candidate=None,
            ablation_design=ablation,
        )
        return result, all_hyps

    def _h_main_from_idea(self, idea_brief) -> Hypothesis:
        if idea_brief is None:
            return Hypothesis(hypothesis_id="H_main", statement="user idea", rationale="no idea brief",
                              novelty_claim="user-provided", verification_path="to be defined")
        return Hypothesis(
            hypothesis_id="H_main",
            statement=idea_brief.user_idea or idea_brief.research_problem,
            rationale=f"User-provided idea for {idea_brief.target_task}",
            novelty_claim=idea_brief.expected_contribution or "user idea to be validated",
            verification_path="Validate via bounded experiment against ablation challengers.",
        )

    def _rank(self, hypotheses: list[Hypothesis], scores: dict) -> list[Hypothesis]:
        return sorted(hypotheses, key=lambda h: self._weighted_score(scores, h.hypothesis_id), reverse=True)

    def _weighted_score(self, scores: dict, hypothesis_id: str) -> float:
        # Average across perspectives of weighted sum of dims, scaled to 0..100.
        per_perspective: list[float] = []
        for perspective in PERSPECTIVES:
            review: CriticReview | None = scores.get(perspective, {}).get(hypothesis_id)
            if review is None:
                continue
            weighted = sum(getattr(review, dim) * ARENA_WEIGHTS[dim] for dim in _DIMS)
            per_perspective.append(weighted / _WEIGHT_SUM)  # 1..10
        if not per_perspective:
            return 0.0
        avg = sum(per_perspective) / len(per_perspective)  # 1..10
        return round(avg * 10.0, 2)  # 10..100

    def _candidates(self, hypotheses: list[Hypothesis], scores: dict, ranked: list[Hypothesis]) -> list[HypothesisArenaCandidate]:
        rank_index = {h.hypothesis_id: i + 1 for i, h in enumerate(ranked)}
        out: list[HypothesisArenaCandidate] = []
        for h in ranked:
            critic_scores = {p: scores.get(p, {}).get(h.hypothesis_id) for p in PERSPECTIVES
                             if scores.get(p, {}).get(h.hypothesis_id) is not None}
            out.append(HypothesisArenaCandidate(
                hypothesis_id=h.hypothesis_id, statement=h.revised_statement or h.statement,
                is_user_idea=False, critic_scores=critic_scores,
                weighted_score=self._weighted_score(scores, h.hypothesis_id), rank=rank_index[h.hypothesis_id],
            ))
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_hypothesis_arena_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 5: code_url 提取（摘要 + PDF 正文）+ BaselineDiscovery 优先用

**Files:**
- Create: `backend/app/tools/code_url_extractor.py`
- Modify: `backend/app/agents/baseline_discovery_agent.py`
- Test: `backend/tests/test_code_url_extractor.py`

**Interfaces:**
- Produces: `extract_code_urls(papers, *, max_pdf=5, transport=None) -> list[Paper]`（原地设 `paper.code_url`，返回 papers）。摘要 regex（所有论文）+ PDF 正文 regex（top-N、有 `pdf_url` 才下载解析）。`BaselineDiscoveryAgent.arun` 优先把有 `code_url` 的论文建成候选（`code_source="paper_abstract"` / `"paper_pdf"`，`verified_repo=True`），无 code_url 才走 GitHub 标题搜。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_code_url_extractor.py
import re

from app.schemas.paper import Paper
from app.tools.code_url_extractor import GITHUB_RE, extract_code_urls


def test_github_regex_matches_owner_repo() -> None:
    m = GITHUB_RE.search("code available at https://github.com/owner/repo for details")
    assert m is not None
    assert m.group(1) == "owner/repo"


def test_extract_from_abstract_sets_code_url() -> None:
    p = Paper(paper_id="p1", title="t",
              abstract="We propose X. Code is available at https://github.com/foo/bar.",
              pdf_url=None)
    out = extract_code_urls([p])
    assert out[0].code_url == "https://github.com/foo/bar"


def test_extract_skips_when_no_github_mention() -> None:
    p = Paper(paper_id="p1", title="t", abstract="no link here", pdf_url=None)
    out = extract_code_urls([p])
    assert out[0].code_url is None


def test_extract_does_not_overwrite_existing_code_url() -> None:
    p = Paper(paper_id="p1", title="t", abstract="see https://github.com/a/b", code_url="https://github.com/keep/this")
    out = extract_code_urls([p])
    assert out[0].code_url == "https://github.com/keep/this"
```

> PDF-download path is tested via monkeypatching the download/parse helpers (see Step 3); the four tests above cover the abstract path + regex + idempotence. Add a PDF-path test in Step 3 if the implementer wants, using `monkeypatch` on the module's `_download_pdf_text`.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_code_url_extractor.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Write the extractor**

```python
# backend/app/tools/code_url_extractor.py
import re
from pathlib import Path

import httpx

from app.schemas.paper import Paper
from app.tools.pdf_parser import parse_pdf_text

GITHUB_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:[)/\s'\"<>]|\.(?:git\b)|$)")
_MAX_PDF_DOWNLOADS = 5


def extract_code_urls(papers: list[Paper], *, max_pdf: int = _MAX_PDF_DOWNLOADS, transport: httpx.AsyncBaseTransport | None = None) -> list[Paper]:
    """Set paper.code_url in-place by mining abstracts (+ PDF full text for top-N).

    Pure-abstract mining is sync (no I/O). PDF mining is async, so this function
    is a sync wrapper that schedules the async PDF mining — kept simple by doing
    abstract mining sync and PDF mining via a separate async helper the workflow
    calls. For testability, the abstract path is what's covered here; the workflow
    task (Task 6) calls `await extract_code_urls_async(...)`.
    """
    for paper in papers:
        if paper.code_url:
            continue
        url = _mine_text(paper.abstract or "")
        if url:
            paper.code_url = url
    return papers


async def extract_code_urls_async(papers: list[Paper], *, max_pdf: int = _MAX_PDF_DOWNLOADS, transport: httpx.AsyncBaseTransport | None = None) -> list[Paper]:
    """Abstract mining (sync) + PDF full-text mining (async, top-N with pdf_url)."""
    extract_code_urls(papers)  # abstract pass
    pdf_candidates = [p for p in papers if not p.code_url and p.pdf_url][:max_pdf]
    for paper in pdf_candidates:
        try:
            text = await _download_pdf_text(paper.pdf_url, transport=transport)
            url = _mine_text(text)
            if url:
                paper.code_url = url
        except Exception:
            continue
    return papers


def _mine_text(text: str) -> str | None:
    if not text:
        return None
    match = GITHUB_RE.search(text)
    if not match:
        return None
    return f"https://github.com/{match.group(1)}"


async def _download_pdf_text(pdf_url: str | None, *, transport: httpx.AsyncBaseTransport | None = None) -> str:
    if not pdf_url:
        return ""
    async with httpx.AsyncClient(timeout=30, transport=transport, follow_redirects=True) as client:
        resp = await client.get(pdf_url, headers={"User-Agent": "TrustSci-Agent/0.1"})
        resp.raise_for_status()
        content = resp.content
    # Write to a temp path and parse with pypdf.
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        pages = parse_pdf_text(tmp_path, max_pages=12)
        return "\n".join(str(p.get("text") or "") for p in pages)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
```

Now modify `backend/app/agents/baseline_discovery_agent.py` `arun` to prefer papers with `code_url`. In `BaselineDiscoveryAgent.arun`, BEFORE the per-paper GitHub search loop, add a paper-code-url pass (insert after `seen_urls: set[str] = set()`):

```python
        # 0) Papers that self-declare a code link (abstract/PDF mining) — highest confidence.
        for paper in (papers or [])[:MAX_PAPERS]:
            url = (paper.code_url or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append(_candidate_from_paper_code_url(paper, task))
```

And add the helper (near `_candidate_from_github`):

```python
def _candidate_from_paper_code_url(paper: Paper, task: str) -> BaselineCandidate:
    source = "paper_pdf" if paper.code_url and paper.code_url else "paper_abstract"
    return BaselineCandidate(
        baseline_id=_stable_id(("paper", paper.paper_id, paper.code_url or "")),
        paper_id=paper.paper_id,
        paper_title=paper.title,
        paper_doi=paper.doi,
        paper_url=paper.source_url,
        code_url=paper.code_url,
        code_source=source,
        task_match=task,
        input_type="unknown",
        verified_repo=True,  # paper-self-declared; RepositoryVerifier may still deepen.
        reproduction_status="pending",
        risks=[],
    )
```

- [ ] **Step 4: Run test to verify it passes + BaselineDiscovery regression**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_code_url_extractor.py tests/test_baseline_discovery_agent.py -v`
Expected: PASS

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 6: 把 Arena + baseline-auto 接入 workflow（classic + LangGraph，seismic 专属，无人工 gate）

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py`
- Modify: `backend/app/workflows/langgraph_workflow.py`
- Test: `backend/tests/test_arena_workflow_integration.py`

**Interfaces:**
- Consumes: `HypothesisArenaAgent`、`CriticArenaAgent`、`ChallengerAgent`、`extract_code_urls_async`、`BaselineDiscoveryAgent`、`RepositoryVerifierAgent`、`NoveltyCheckerAgent`（S2 已建）。
- Produces: seismic run 在 `scientific_data_profile` 之后走 `arena`（替代线性 `hypothesis_debate`）→ `extract_code_urls` → `baseline_discover` → `baseline_verify`（top-3）→ `experiment_design`。非 seismic 保持 `_generate_and_critique`。Arena 自动选 Top1（无 `_pause_for_human`）。`run.arena_result` / `run.baseline_candidates` 自动填。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_arena_workflow_integration.py
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
async def test_seismic_run_uses_arena_and_auto_baseline(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)

    # Stub the arena agent to avoid real LLM/parallel cost.
    async def fake_arena_arun(self, mode, gaps, evidence, data_profiles, idea_brief, papers, *, run_id):
        from app.schemas.arena import HypothesisArenaResult
        from app.schemas.hypothesis import Hypothesis
        h = Hypothesis(hypothesis_id="H1", statement="s", rationale="r", novelty_claim="n", verification_path="v", selected=True)
        result = HypothesisArenaResult(arena_id="a1", mode=mode, candidates=[], ranking=["H1"], selected_for_experiment="H1", switchback_candidate=None)
        return result, [h]
    monkeypatch.setattr(workflow.arena_agent.__class__, "arun", fake_arena_arun)

    # Stub baseline discovery + verify (no real GitHub).
    async def fake_extract(papers, *, max_pdf=5, transport=None):
        return papers
    monkeypatch.setattr("app.workflows.scientist_workflow.extract_code_urls_async", fake_extract)

    async def fake_discover(self, papers, task, *, run_id):
        from app.schemas.baseline import BaselineCandidate
        return [BaselineCandidate(baseline_id="b1", paper_id="p1", paper_title="t", code_url="https://github.com/a/b", code_source="paper_abstract", task_match="seismic", input_type="waveform", verified_repo=True)]
    monkeypatch.setattr(workflow.baseline_discovery.__class__, "arun", fake_discover)

    async def fake_verify(self, candidate, *, run_id):
        return candidate
    monkeypatch.setattr(workflow.repo_verifier.__class__, "arun", fake_verify)

    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints(max_papers=1), mode="discovery")

    await workflow._run_arena(run)
    assert run.arena_result is not None
    assert run.arena_result.selected_for_experiment == "H1"
    assert run.hypotheses[0].selected is True

    await workflow._extract_code_urls(run)
    await workflow._discover_baselines_auto(run)
    await workflow._verify_baselines_auto(run)
    assert run.baseline_candidates
    assert run.baseline_candidates[0].code_url == "https://github.com/a/b"


@pytest.mark.asyncio
async def test_non_seismic_run_skips_arena(monkeypatch) -> None:
    settings = Settings(dashscope_api_key="", max_papers=2)
    workflow = ScientistWorkflow(settings)
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints(max_papers=1), mode="discovery")
    # _run_after_evidence_review for non-seismic should call the existing _generate_and_critique, not arena.
    # Just assert the arena method is a no-op / not invoked by checking arena_result stays None after a non-seismic arena call.
    await workflow._run_arena(run)
    # non-seismic arena is a no-op
    assert run.arena_result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_arena_workflow_integration.py -v`
Expected: FAIL — `ScientistWorkflow` has no `arena_agent` / `_run_arena` etc.

- [ ] **Step 3: Modify ScientistWorkflow**

In `backend/app/workflows/scientist_workflow.py`, add imports:

```python
from app.agents.challenger_agent import ChallengerAgent
from app.agents.critic_arena_agent import CriticArenaAgent
from app.agents.hypothesis_arena_agent import HypothesisArenaAgent
from app.tools.code_url_extractor import extract_code_urls_async
```

In `__init__`, after `self.seismic_adapter = SeismicDataAdapter(settings.data_dir)` (added in S1), add:

```python
        self.critic_arena = CriticArenaAgent(self.llm)
        self.challenger = ChallengerAgent(self.llm)
        self.arena_agent = HypothesisArenaAgent(
            hypothesis_agent=self.hypothesis_agent,
            critic_arena=self.critic_arena,
            revision=self.revision_agent,
            challenger=self.challenger,
        )
```

Add the four seismic step methods (place after `_generate_and_critique`):

```python
    async def _run_arena(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            run.steps[-1].summary = "Skipped arena (non-seismic domain)."
            return
        evidence = _workflow_evidence(run)
        gaps = await self.gap_finder.arun(run.knowledge_cards, evidence, run.data_profiles, run_id=run.run_id)
        result, hypotheses = await self.arena_agent.arun(
            run.mode, gaps, evidence, run.data_profiles, run.idea_brief, run.papers, run_id=run.run_id,
        )
        run.arena_result = result
        run.hypotheses = hypotheses
        selected = _selected_hypothesis(run.hypotheses)
        run.steps[-1].summary = (
            f"Arena ({result.mode}) ranked {len(result.ranking)} hypotheses; "
            f"selected={result.selected_for_experiment}, switchback={result.switchback_candidate}."
        ) + (f" Selected: {selected.statement[:80]}." if selected else "")

    async def _extract_code_urls(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification" or not run.papers:
            run.steps[-1].summary = "Skipped code-url extraction."
            return
        await extract_code_urls_async(run.papers, max_pdf=5)
        with_code = sum(1 for p in run.papers if p.code_url)
        run.steps[-1].summary = f"Mined code URLs from abstracts/PDFs; {with_code}/{len(run.papers)} papers have a code link."

    async def _discover_baselines_auto(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            run.steps[-1].summary = "Skipped baseline discovery (non-seismic)."
            return
        if run.idea_brief is not None or any(p.code_url for p in run.papers):
            run.novelty_report = await self.novelty_checker.arun(run.papers, run.idea_brief, run_id=run.run_id)
        task = "seismic event classification"
        run.baseline_candidates = await self.baseline_discovery.arun(run.papers, task, run_id=run.run_id)
        run.steps[-1].summary = f"Discovered {len(run.baseline_candidates)} baseline candidates (auto)."

    async def _verify_baselines_auto(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification" or not run.baseline_candidates:
            run.steps[-1].summary = "Skipped repo verification (no candidates)."
            return
        # Auto-verify only the unverified (github_search) candidates, top-3 (cost + rate-limit control).
        # paper-code candidates are already verified_repo=True (paper-self-declared).
        to_verify = [c for c in run.baseline_candidates if not c.verified_repo][:3]
        for candidate in to_verify:
            try:
                updated = await self.repo_verifier.arun(candidate, run_id=run.run_id)
                idx = run.baseline_candidates.index(candidate)
                run.baseline_candidates[idx] = updated
            except Exception:
                continue
        verified = sum(1 for c in run.baseline_candidates if c.verified_repo)
        run.steps[-1].summary = f"Auto-verified {len(to_verify)} unverified repos; {verified}/{len(run.baseline_candidates)} now verified."
```

Add the helper: none new needed (`_selected_hypothesis` and `_workflow_evidence` already exist in `scientist_workflow.py`).

Modify `_run_after_evidence_review` to branch on seismic. The current method (S1) is:

```python
    async def _run_after_evidence_review(self, run: ResearchRun) -> None:
        await self._step(run, "scientific_data_profile", self._profile_scientific_data)
        await self._step(run, "hypothesis_debate", self._generate_and_critique)
        await self._step(run, "experiment_design", self._design_experiment)
        await self._step(run, "report_writer", self._write_report)
        await self._step(run, "claim_verification", self._verify_claims)
        await self._step(run, "report_revision", self._revise_report_after_audit)
        await self._step(run, "claim_reverification", self._verify_claims)
        await self._step(run, "report_translation", self._translate_report)
        run.status = RunStatus.completed
        run.current_stage = "completed"
        run.progress = 1.0
        run.updated_at = utc_now()
        self._write_workspace(run)
```

Replace the body with a seismic-branching version:

```python
    async def _run_after_evidence_review(self, run: ResearchRun) -> None:
        await self._step(run, "scientific_data_profile", self._profile_scientific_data)
        if run.domain == "seismic_event_classification":
            await self._step(run, "arena", self._run_arena)
            await self._step(run, "extract_code_urls", self._extract_code_urls)
            await self._step(run, "baseline_discover", self._discover_baselines_auto)
            await self._step(run, "baseline_verify", self._verify_baselines_auto)
        else:
            await self._step(run, "hypothesis_debate", self._generate_and_critique)
        await self._step(run, "experiment_design", self._design_experiment)
        await self._step(run, "report_writer", self._write_report)
        await self._step(run, "claim_verification", self._verify_claims)
        await self._step(run, "report_revision", self._revise_report_after_audit)
        await self._step(run, "claim_reverification", self._verify_claims)
        await self._step(run, "report_translation", self._translate_report)
        run.status = RunStatus.completed
        run.current_stage = "completed"
        run.progress = 1.0
        run.updated_at = utc_now()
        self._write_workspace(run)
```

> Note: the arena needs gaps; `_run_arena` calls the existing `self.gap_finder.arun(run.knowledge_cards, evidence, run.data_profiles, ...)` (same as `_generate_and_critique` does) — do not invent a `knowledge_cards_to_gaps` method.

- [ ] **Step 4: Modify LangGraphWorkflow to mirror the seismic branch**

In `backend/app/workflows/langgraph_workflow.py`, the current graph has `scientific_data_profile → hypothesis_debate → experiment_design` (from `_LINEAR_STEPS` + edges). The seismic run goes through these nodes. To branch seismic to arena, modify `_build_graph`:

Replace the block:
```python
        graph.add_edge("scientific_data_profile", "hypothesis_debate")
        graph.add_edge("hypothesis_debate", "experiment_design")
```
with a conditional branch on domain:

```python
        graph.add_conditional_edges(
            "scientific_data_profile",
            self._route_after_data_profile,
            {"arena": "arena", "hypothesis_debate": "hypothesis_debate"},
        )
        # Seismic arena + baseline auto chain (S3).
        graph.add_node("arena", self._make_step_node("arena", "_run_arena"))
        graph.add_node("extract_code_urls", self._make_step_node("extract_code_urls", "_extract_code_urls"))
        graph.add_node("baseline_discover", self._make_step_node("baseline_discover", "_discover_baselines_auto"))
        graph.add_node("baseline_verify", self._make_step_node("baseline_verify", "_verify_baselines_auto"))
        graph.add_edge("arena", "extract_code_urls")
        graph.add_edge("extract_code_urls", "baseline_discover")
        graph.add_edge("baseline_discover", "baseline_verify")
        graph.add_edge("baseline_verify", "experiment_design")
        graph.add_edge("hypothesis_debate", "experiment_design")
```

Add the routing method (near `_route_after_mining`):

```python
    def _route_after_data_profile(self, state: WorkflowState) -> str:
        run = state["run"]
        return "arena" if run.domain == "seismic_event_classification" else "hypothesis_debate"
```

Also remove `("hypothesis_debate", "_generate_and_critique")` from `_LINEAR_STEPS`? No — keep it (non-seismic still uses the hypothesis_debate node via the `hypothesis_debate` edge). The `_LINEAR_STEPS` registers the node; the conditional edge routes to it for non-seismic. Leave `_LINEAR_STEPS` as-is.

- [ ] **Step 5: Run test to verify it passes + full suite**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_arena_workflow_integration.py tests/test_langgraph_workflow.py -v`
Then full suite: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q`
Expected: PASS (the langgraph step-name assertion in `test_langgraph_workflow_completes_sync_run` uses a non-seismic run, so its step list still ends with `hypothesis_debate` — unchanged. The seismic path is exercised by the new integration test with stubs.)

- [ ] **Step 6: Skip commit (local-only).**

---

### Task 7: 前端 Arena 面板 + 接入 seismic 工作区

**Files:**
- Create: `frontend/components/workbench/HypothesisArenaPanel.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/workbench/Workbench.tsx`
- Test: manual.

**Interfaces:**
- Produces: `HypothesisArenaPanel({run})` 显示 `run.arena_result`：候选排名表（hypothesis_id / statement / weighted_score / rank / is_user_idea 标记）、Top1/Top2、mode、ablation_design（Idea Refinement 时）。seismic 工作区 grid 加该面板。

- [ ] **Step 1: Add arena_result type to `frontend/lib/api.ts`**

In the `ResearchRun` type, after `novelty_report?: {...}` block, add:

```typescript
  arena_result?: {
    arena_id: string;
    mode: string;
    arena_level: string;
    candidates: Array<{
      hypothesis_id: string;
      statement: string;
      is_user_idea: boolean;
      weighted_score: number;
      rank: number;
      critic_scores?: Record<string, {
        novelty: number; self_consistency: number; verifiability: number;
        data_availability: number; feasibility: number; evidence_support: number;
        reproducibility: number; competition_fit: number; risk: string; revision_advice: string;
      }>;
    }>;
    ranking: string[];
    selected_for_experiment: string;
    switchback_candidate?: string | null;
    ablation_design: Array<{ challenge_id: string; tests_innovation_point: string; expected_insight: string; derivation_from_main: string }>;
  };
```

- [ ] **Step 2: Create `frontend/components/workbench/HypothesisArenaPanel.tsx`**

```tsx
import { Trophy } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function HypothesisArenaPanel({ run }: { run: ResearchRun | null }) {
  const arena = run?.arena_result;
  if (!arena) {
    return (
      <section className="panel span-8">
        <div className="panel-heading"><h2><Trophy size={16} /> Hypothesis Arena</h2></div>
        <p className="muted">等待 Arena 竞技完成（seismic run 自动触发）。</p>
      </section>
    );
  }
  const sorted = [...(arena.candidates || [])].sort((a, b) => (a.rank || 0) - (b.rank || 0));
  return (
    <section className="panel span-8">
      <div className="panel-heading">
        <h2><Trophy size={16} /> Hypothesis Arena</h2>
        <div className="actions">
          <span className="badge">{arena.mode}</span>
          <span className="badge">{arena.arena_level}</span>
        </div>
      </div>
      <div className="item">
        <div className="item-title">Top1 (selected): {arena.selected_for_experiment}</div>
        {arena.switchback_candidate ? <div className="muted">Switchback 备选: {arena.switchback_candidate}</div> : null}
      </div>
      <div className="list">
        {sorted.map((c) => (
          <article className="item" key={c.hypothesis_id}>
            <div className="item-title">#{c.rank} {c.hypothesis_id}{c.is_user_idea ? " (用户创意)" : ""}</div>
            <div className="muted">{c.statement}</div>
            <div className="item-actions">
              <span className={`badge ${c.hypothesis_id === arena.selected_for_experiment ? "good" : ""}`}>
                score {c.weighted_score.toFixed(1)}
              </span>
            </div>
          </article>
        ))}
      </div>
      {arena.ablation_design && arena.ablation_design.length > 0 && (
        <div className="item">
          <div className="item-title">消融设计 (Idea Refinement)</div>
          {arena.ablation_design.map((a) => (
            <div className="muted" key={a.challenge_id}>
              {a.challenge_id}: 测 {a.tests_innovation_point} — {a.expected_insight}（{a.derivation_from_main}）
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 3: Wire into `frontend/components/workbench/Workbench.tsx`**

Add import (with the other panel imports):

```tsx
import { HypothesisArenaPanel } from "./HypothesisArenaPanel";
```

In the seismic `<section className="content">` grid (the one built in S2 Task 7), add the Arena panel between SeismicOverviewPanel and LiteratureBoard:

```tsx
          <div className="grid">
            <SeismicOverviewPanel run={run} />
            <HypothesisArenaPanel run={run} />
            <LiteratureBoard run={run} />
            <BaselineBoard run={run} busy={baselineBusy} onDiscover={handleDiscoverBaselines} onVerify={handleVerifyBaseline} />
            <WorkspacePanel run={run} />
          </div>
```

- [ ] **Step 4: Manual verification**

Open http://localhost:3000 → Seismic Expert → 发现 or 创意精修 → 启动 a seismic run. After it completes, the Seismic workspace shows:
- SeismicOverviewPanel (mode/intent/idea/profile)
- **HypothesisArenaPanel** (ranked candidates, Top1 selected, ablation design if idea_refinement)
- LiteratureBoard (papers)
- BaselineBoard (auto-filled candidates with code_url from papers where found + GitHub fallback; top-3 auto-verified)

Confirm Classic Workflow still runs unchanged.

- [ ] **Step 5: Skip commit (local-only).**

---

## S3 验收（全量回归 + live）

- [ ] **Step 6: Run full backend suite**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q
```

Expected: all green, including new tests (test_arena_schemas, test_critic_arena_agent, test_hypothesis_arena_agent, test_challenger_agent, test_code_url_extractor, test_arena_workflow_integration) + S1/S2/v1-v2 regression.

- [ ] **Step 7: Live acceptance**

Create a seismic run (discovery + idea_refinement), confirm via `GET /api/runs/{id}`:
- `arena_result` populated (ranking, selected_for_experiment, candidates with weighted_score).
- `hypotheses[0].selected == True` (auto, no human gate).
- `papers[*].code_url` set for papers whose abstract/PDF mentions github.
- `baseline_candidates` auto-populated (paper-code candidates + GitHub fallback), top-3 `verified_repo`/`reproducibility_score` set.

## 已知 S3 局限（后续 Sprint 处理）

- Elo 竞技（pairwise/evolution）→ S7（arena_level 切 elo_tournament，接口不变）。
- Idea Refinement 的 switchback → S5（且自动，无 interrupt）。
- 代码能否运行（Code Experiment Loop）→ S4。
- PDF 正文挖 code 只对 top-5、有 pdf_url 的论文做；付费墙论文无 pdf_url 抓不到。
- RepositoryVerifier 自动只验证 top-3（成本/rate limit）；全量验证可手动点 BaselineBoard 的 Verify Repo（S2 端点保留）。
- 人工 gate（hypothesis selection / evidence freeze / switchback confirm）全部后置，按用户要求 S3 走全自动。
