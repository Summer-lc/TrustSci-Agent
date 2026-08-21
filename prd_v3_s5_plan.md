# v3 Sprint S5 实施计划：统一反馈循环（Novelty 检查 + Baseline 两层门 + Macro-ReAct + Switchback）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 S4 图之上叠加三个带 cap 的反馈循环——(A) Arena 后的 novelty/prior-art 检查驱动假设处置，(B) baseline_verify 后的两层质量门驱动重搜+依赖感知重跑，(C) code_experiment 后的 macro repair + switchback——都用 dirty-flag + 独立计数器，全自动无 gate，诚实分流出 research-grade / degraded / negative。

**Architecture:** 三个 LangGraph cycle（条件边读计数器）：`arena→novelty_check→(already_done?→arena regen cap2 : extract_code_urls)`、`baseline_verify→baseline_quality_gate→(research fail?→re_search_literature→(evidence_changed?→evidence_ledger全链 : baseline_discover) cap2 : experiment_design)`、`code_experiment→macro_react→(bad?→macro cap1→switchback Top2→negative : report_writer)`。classic `_run_after_evidence_review` 线性透传新 step（不实现 cycle）。CodeWriter 加 `macro` mode；NoveltyCheckerAgent 扩展 5 类 verdict；RevisionAgent 确定性应用 claim_revision；BaselineGate 纯函数谓词。dirty flag (`evidence_changed`/`hypothesis_changed`/`baseline_changed`) + 计数器 (`novelty_round`/`re_search_round`/`macro_round`/`switchback_used`) 在 ResearchRun，inner 计数不重置防嵌套爆炸。

**Tech Stack:** Python 3.11 / FastAPI / Pydantic / LangChain LCEL / LangGraph StateGraph / pytest / Next.js。

## Global Constraints

- **不 commit**：所有改动留本地工作区（每 Task Step 5 = "Skip commit (local-only)"）。
- 后端测试在 Docker dev 栈：`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest <path> -v`。容器 WORKDIR `/app`，`experiments/` + `data/` 已挂载（S4 Task 1 加的）。
- `WORKFLOW_ENGINE=langgraph`，真实 Qwen `qwen3.7-max`。agent 走 `LLMClientRunnable`+`build_agent_prompt`+`FallbackParser`，调 `QwenClient.complete()`，审计日志 `data/outputs/llm_calls/{run_id}.jsonl`。
- **S5 只对 `run.domain == "seismic_event_classification"` 启用循环**；非 seismic 走原路径。S5 新节点（novelty_check/baseline_quality_gate/re_search_literature/macro_react）放 seismic 分支内或条件边跳过非 seismic，**不污染非 seismic step_names**（与 S4 code_experiment 的无条件 no-op 模式不同——S5 节点条件路由，非 seismic 不经过）。
- **全自动无人工 gate**：switchback 也自动，不 `interrupt()`。
- **三级升级，inner cap 不重置**：macro_round cap=1（全局预算，Top2 不享 macro）、switchback cap=1（仅 Top2，无 Top3）、novelty regen cap=2、re_search cap=2。每个循环独立计数器，升级到外层不重置 inner。
- **Macro 触发**：`outcome=failed` OR (`completed_negative AND baseline_metric - method_metric >= 0.05`，accuracy 优先 fallback macro_f1)。窄负(<0.05) 诚实接受。`max_macro_rounds=1`。
- **Baseline 两层门**：运行门（≥1 可用，harness_trivial 兜底，恒过）+ 科研门（`external_verified_model_baselines >= 1`，即 harness_trivial + ≥1 verified_repo）。科研门 fail → 重搜 cap 2 → 仍 0 verified → `comparison_grade="degraded"` 降级运行门继续。`verified_repo` 已编码 `is_model_baseline AND matches_task_domain AND repo_type=model_code AND reproducibility_score>=0.6 AND status==verified`。
- **Novelty 5 verdict**：`novel`/`dataset_only`→不动；`transfer_applicability`/`similar_work`→claim_revision 由 RevisionAgent 确定性应用；`already_done`→prior_art 论文进 baseline 候选 + Arena 重生成（注入"避开 prior_art"反馈，cap 2，仍撞车→`novelty_status="low_novelty"` 继续跑）。
- **依赖感知重跑**：只换 repo→`baseline_discover+verify`；换论文/evidence→`evidence_ledger→literature_mining→paper_classification→scientific_data_profile→arena→novelty_check→extract_code_urls→baseline_discover→baseline_verify→baseline_quality_gate`（全链）。
- **范围**：S5 只做反馈循环 + Feedback Loop Panel（前端）。§5.4 的 Result Evaluator/Ablation Agent/Result Interpreter/v3 报告 provenance 字段拆到 S5.5/S6。
- YAGNI：schema/字段按 S5 需要建。不实现 `verified_repo` baseline 分支（S7）。
- 文件路径相对仓库根 `d:/For work/TrustSci-Agent/`。

## File Structure

- **Create** `backend/app/schemas/feedback_loop.py` — `NoveltyVerdict` + `BaselineGateStatus`。
- **Create** `backend/tests/test_s5_schemas.py`
- **Modify** `backend/app/schemas/code_experiment.py` — 加 `trigger`。
- **Modify** `backend/app/schemas/run.py` — 加状态旗 + 计数器 + `novelty_verdict`/`baseline_gate_status`。
- **Modify** `backend/app/agents/novelty_checker_agent.py` — 5 类 verdict + `hypothesis` 参数 + `claim_revision`/`prior_art_paper_ids`。
- **Modify** `backend/app/agents/revision_agent.py` — `run(hypotheses, novelty_verdict)` 应用 `claim_revision`。
- **Modify** `backend/app/agents/hypothesis_agent.py` — 接受 `avoid_prior_art: list[str] | None`。
- **Modify** `backend/app/agents/code_writer_agent.py` — 加 `macro` mode。
- **Modify** `backend/app/tools/literature_router.py` — `per_source_limit = max(max_papers + 2, 8)`（修 S3.5 遗留）。
- **Modify** `backend/app/workflows/scientist_workflow.py` — 新 step 方法 `_run_novelty_check`/`_evaluate_baseline_gate`/`_re_search_literature`/`_run_macro_react` + `_execute_micro_loop` 重构 + `_run_after_evidence_review` 线性透传 + `_route_*` 路由函数。
- **Modify** `backend/app/workflows/langgraph_workflow.py` — 4 新节点 + 3 cycle 条件边。
- **Create** `backend/tests/test_novelty_checker_agent_s5.py`
- **Create** `backend/tests/test_revision_agent_s5.py`
- **Create** `backend/tests/test_baseline_gate.py`
- **Create** `backend/tests/test_re_search_literature.py`
- **Create** `backend/tests/test_code_writer_macro.py`
- **Create** `backend/tests/test_macro_react.py`
- **Create** `backend/tests/test_s5_langgraph_cycles.py`
- **Modify** `backend/tests/test_langgraph_workflow.py` — 非 seismic step_names 不变（S5 节点条件跳过）。
- **Create** `frontend/components/workbench/FeedbackLoopPanel.tsx`
- **Modify** `frontend/lib/api.ts` — NoveltyVerdict/BaselineGateStatus/loop-state 类型 + Run 字段。
- **Modify** `frontend/components/workbench/Workbench.tsx` — seismic 挂 FeedbackLoopPanel。

---

### Task 1: Schema + 状态旗 + 计数器

**Files:**
- Create: `backend/app/schemas/feedback_loop.py`
- Modify: `backend/app/schemas/code_experiment.py`
- Modify: `backend/app/schemas/run.py`
- Test: `backend/tests/test_s5_schemas.py`

**Interfaces:**
- Produces: `NoveltyVerdict`、`BaselineGateStatus` schema；`CodeExperimentResult.trigger`；`ResearchRun` 加 `novelty_verdict`/`novelty_status`/`novelty_round`/`baseline_gate_status`/`re_search_round`/`evidence_changed`/`hypothesis_changed`/`baseline_changed`/`macro_round`/`switchback_used`/`code_experiment_mode`。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_s5_schemas.py
from app.schemas.feedback_loop import NoveltyVerdict, BaselineGateStatus
from app.schemas.code_experiment import CodeExperimentResult
from app.schemas.run import ResearchRun, ResearchConstraints


def test_novelty_verdict_defaults() -> None:
    v = NoveltyVerdict()
    assert v.verdict == "novel"
    assert v.claim_revision is None
    assert v.prior_art_paper_ids == []
    assert v.reasoning == ""


def test_baseline_gate_status_defaults() -> None:
    g = BaselineGateStatus()
    assert g.external_verified_model_baselines == 0
    assert g.comparable_count == 1  # harness_trivial
    assert g.run_gate_passed is True
    assert g.research_gate_passed is False
    assert g.comparison_grade == "degraded"


def test_code_experiment_trigger_default() -> None:
    ce = CodeExperimentResult()
    assert ce.trigger == "initial"


def test_run_s5_fields_default() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints())
    assert run.novelty_verdict is None
    assert run.novelty_status == "not_checked"
    assert run.novelty_round == 0
    assert run.baseline_gate_status is None
    assert run.re_search_round == 0
    assert run.evidence_changed is False
    assert run.hypothesis_changed is False
    assert run.baseline_changed is False
    assert run.macro_round == 0
    assert run.switchback_used is False
    assert run.code_experiment_mode is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s5_schemas.py -v`
Expected: FAIL (missing fields)

- [ ] **Step 3: Implement schema**

`backend/app/schemas/feedback_loop.py`:
```python
from typing import Literal

from pydantic import BaseModel, Field


class NoveltyVerdict(BaseModel):
    verdict: Literal["novel", "transfer_applicability", "already_done",
                     "dataset_only", "similar_work"] = "novel"
    claim_revision: str | None = None
    prior_art_paper_ids: list[str] = Field(default_factory=list)
    overlap_points: list[str] = Field(default_factory=list)
    retainable_novelty: list[str] = Field(default_factory=list)
    reasoning: str = ""
    # backward-compat with the old novelty_report dict fields
    similar_work: list[dict] = Field(default_factory=list)
    has_public_code: bool = False


class BaselineGateStatus(BaseModel):
    external_verified_model_baselines: int = 0
    comparable_count: int = 1  # harness_trivial always counts as 1
    run_gate_passed: bool = True
    research_gate_passed: bool = False
    insufficient_reasons: list[str] = Field(default_factory=list)
    comparison_grade: Literal["research", "degraded"] = "degraded"
```

`backend/app/schemas/code_experiment.py` — add to `CodeExperimentResult`:
```python
    trigger: Literal["initial", "macro", "switchback"] = "initial"
```
(import `Literal` if not already.)

`backend/app/schemas/run.py` — add import + fields. After `from app.schemas.code_experiment import CodeExperimentResult`:
```python
from app.schemas.feedback_loop import BaselineGateStatus, NoveltyVerdict
```
After `code_experiment: CodeExperimentResult | None = None`:
```python
    # S5 feedback-loop state
    novelty_verdict: NoveltyVerdict | None = None
    novelty_status: Literal["not_checked", "ok", "low_novelty"] = "not_checked"
    novelty_round: int = 0
    baseline_gate_status: BaselineGateStatus | None = None
    re_search_round: int = 0
    evidence_changed: bool = False
    hypothesis_changed: bool = False
    baseline_changed: bool = False
    macro_round: int = 0
    switchback_used: bool = False
    code_experiment_mode: str | None = None
```
(`Literal` is already imported in run.py via `from typing import Literal`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s5_schemas.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 2: NoveltyCheckerAgent 扩展 + RevisionAgent 应用 claim_revision

**Files:**
- Modify: `backend/app/agents/novelty_checker_agent.py`
- Modify: `backend/app/agents/revision_agent.py`
- Test: `backend/tests/test_novelty_checker_agent_s5.py`, `backend/tests/test_revision_agent_s5.py`

**Interfaces:**
- `NoveltyCheckerAgent.arun(papers, hypothesis, idea_brief, *, run_id) -> NoveltyVerdict`（加 `hypothesis: Hypothesis | None` 参数）。
- `RevisionAgent.run(hypotheses, novelty_verdict=None)`：若 `novelty_verdict.claim_revision` 存在，应用到 Top1（`revised_statement = claim_revision` + `RevisionRecord`）。无 novelty 时保留原 suffix 逻辑。

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_novelty_checker_agent_s5.py
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
```

```python
# backend/tests/test_revision_agent_s5.py
from app.agents.revision_agent import RevisionAgent
from app.schemas.feedback_loop import NoveltyVerdict
from app.schemas.hypothesis import Hypothesis


def test_revision_applies_claim_revision_to_top1() -> None:
    h = Hypothesis(hypothesis_id="H1", statement="original claim", rationale="r",
                   novelty_claim="n", verification_path="v", selected=True)
    verdict = NoveltyVerdict(verdict="similar_work",
                             claim_revision="narrowed claim: verifiable improvement path")
    RevisionAgent().run([h], novelty_verdict=verdict)
    assert h.revised_statement == "narrowed claim: verifiable improvement path"
    assert h.revision_history
    assert "novelty" in h.revision_history[-1].rationale.lower()


def test_revision_keeps_suffix_when_no_novelty() -> None:
    h = Hypothesis(hypothesis_id="H1", statement="original claim", rationale="r",
                   novelty_claim="n", verification_path="v", selected=True)
    RevisionAgent().run([h], novelty_verdict=None)
    # original deterministic suffix path
    assert h.revised_statement is not None
    assert "bounded" in h.revised_statement.lower() or h.revised_statement != h.statement
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_novelty_checker_agent_s5.py tests/test_revision_agent_s5.py -v`
Expected: FAIL (signature mismatch / missing fields)

- [ ] **Step 3: Implement**

`backend/app/agents/novelty_checker_agent.py` — extend. New SYSTEM_PROMPT (5 verdicts), new `arun(papers, hypothesis, idea_brief, *, run_id) -> NoveltyVerdict`, new `_normalize` producing `NoveltyVerdict`, fallback deterministic (no prior art found → `novel`). Keep old `similar_work`/`has_public_code` fields. The user prompt includes the Top1 hypothesis statement + novelty_claim + the papers (titles/abstracts) + instruction to judge "same task + same core method + same validation goal". Return JSON with `verdict`/`claim_revision`/`prior_art_paper_ids`/`overlap_points`/`retainable_novelty`/`reasoning`. Fallback: `NoveltyVerdict(verdict="novel", reasoning="LLM unavailable; defaulting to novel")`.

> Pattern: mirror `paper_type_classifier_agent.py` (`build_agent_prompt` + `LLMClientRunnable.bind(fallback=..., agent="novelty_checker")` + a `FallbackParser`/custom Runnable normalizing to `NoveltyVerdict`). `hypothesis` is the Top1 from `_selected_hypothesis(run.hypotheses)`; `idea_brief` passed in idea_refinement mode. The agent uses `response_format=LLMResponseFormat.json` (default — it returns JSON, unlike CodeWriter).

`backend/app/agents/revision_agent.py` — extend signature:
```python
def run(self, hypotheses: list[Hypothesis], novelty_verdict=None) -> list[Hypothesis]:
    for hypothesis in hypotheses:
        if novelty_verdict and novelty_verdict.claim_revision and hypothesis.selected:
            after = novelty_verdict.claim_revision
            if after != (hypothesis.revised_statement or hypothesis.statement):
                hypothesis.revised_statement = after
                hypothesis.revision_history.append(RevisionRecord(
                    before=hypothesis.revised_statement or hypothesis.statement,
                    after=after,
                    rationale=f"novelty verdict: {novelty_verdict.verdict} — claim narrowed",
                ))
            continue
        # original deterministic suffix path
        after = _revised_statement(hypothesis)
        if after != hypothesis.statement:
            hypothesis.revised_statement = after
            hypothesis.revision_history.append(RevisionRecord(
                before=hypothesis.statement, after=after,
                rationale=_revision_rationale(hypothesis)))
    return hypotheses
```
(import `RevisionRecord` already there; `novelty_verdict: NoveltyVerdict | None = None`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_novelty_checker_agent_s5.py tests/test_revision_agent_s5.py -v`
Expected: PASS

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 3: BaselineGate 谓词 + Re-search step + per_source_limit 修

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py` — `_evaluate_baseline_gate` + `_re_search_literature` step 方法 + `_baseline_gate_status(candidates)` 纯函数。
- Modify: `backend/app/tools/literature_router.py:54` — `per_source_limit`。
- Test: `backend/tests/test_baseline_gate.py`, `backend/tests/test_re_search_literature.py`

**Interfaces:**
- `_baseline_gate_status(candidates) -> BaselineGateStatus`（纯函数，5 不足条件）。
- `_evaluate_baseline_gate(run)` step：seismic 调纯函数存 `run.baseline_gate_status`；非 seismic no-op。
- `_re_search_literature(run)` step：seismic 用聚焦查询重搜 + 替换 dataset/no-code 论文 + 设 `evidence_changed` + `re_search_round++`；非 seismic no-op。

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_baseline_gate.py
from app.workflows.scientist_workflow import _baseline_gate_status
from app.schemas.baseline import BaselineCandidate


def _c(**kw) -> BaselineCandidate:
    base = dict(baseline_id="b", paper_id="p", paper_title="t", code_url="https://github.com/a/b",
                code_source="github_search", task_match="seismic", input_type="waveform", stars=10)
    base.update(kw)
    return BaselineCandidate(**base)


def test_gate_research_grade_with_one_verified() -> None:
    cands = [_c(verified_repo=True, is_model_baseline=True, matches_task_domain=True,
                repo_type="model_code", reproducibility_score=0.8)]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is True
    assert g.comparison_grade == "research"
    assert g.external_verified_model_baselines == 1
    assert g.comparable_count == 2  # 1 verified + harness_trivial


def test_gate_degraded_when_zero_verified() -> None:
    cands = [_c(verified_repo=False, is_model_baseline=True, matches_task_domain=True,
                repo_type="model_code", reproducibility_score=0.5)]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert g.comparison_grade == "degraded"
    assert "no verified external model baseline" in g.insufficient_reasons


def test_gate_flags_dataset_only_candidates() -> None:
    cands = [_c(verified_repo=False, is_model_baseline=False, repo_type="dataset_only")]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert any("dataset" in r or "docs" in r or "empty" in r for r in g.insufficient_reasons)


def test_gate_flags_task_mismatch() -> None:
    cands = [_c(verified_repo=False, is_model_baseline=True, matches_task_domain=False,
                repo_type="model_code", reproducibility_score=0.8)]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert any("task" in r for r in g.insufficient_reasons)


def test_gate_flags_low_repro() -> None:
    cands = [_c(verified_repo=False, is_model_baseline=True, matches_task_domain=True,
                repo_type="model_code", reproducibility_score=0.4)]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert any("reproducibility" in r.lower() for r in g.insufficient_reasons)
```

```python
# backend/tests/test_re_search_literature.py
import pytest
from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


@pytest.mark.asyncio
async def test_re_search_replaces_dataset_papers_and_sets_evidence_changed(monkeypatch, tmp_path):
    wf = ScientistWorkflow(Settings(dashscope_api_key="", max_papers=3))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints())
    from app.schemas.paper import Paper
    run.papers = [
        Paper(paper_id="p1", title="STEAD dataset", baseline_eligible=False, paper_role="dataset_benchmark"),
        Paper(paper_id="p2", title="Seismic CNN model", baseline_eligible=True, paper_role="method_model"),
    ]
    async def fake_search(queries, *, max_papers, enable_semantic_scholar=False, enable_arxiv=True, domain=""):
        return [Paper(paper_id="new1", title="EQTransformer reproduction github", baseline_eligible=True)]
    monkeypatch.setattr(wf.literature_router, "search", fake_search)
    await wf._re_search_literature(run)
    assert run.re_search_round == 1
    assert run.evidence_changed is True  # dataset paper replaced
    assert all(p.paper_id != "p1" for p in run.papers)  # dataset paper gone


@pytest.mark.asyncio
async def test_re_search_noop_non_seismic(monkeypatch, tmp_path):
    wf = ScientistWorkflow(Settings(dashscope_api_key=""))
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    await wf._re_search_literature(run)
    assert run.re_search_round == 0
    assert run.evidence_changed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baseline_gate.py tests/test_re_search_literature.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

In `backend/app/workflows/scientist_workflow.py`, add module-level pure function:
```python
def _baseline_gate_status(candidates: list[BaselineCandidate]) -> BaselineGateStatus:
    verified = [c for c in candidates if c.verified_repo]
    ext_verified = len(verified)
    comparable = ext_verified + 1  # harness_trivial always available
    reasons: list[str] = []
    if ext_verified == 0:
        reasons.append("no verified external model baseline")
    if candidates and all(
        (c.repo_type in ("dataset_only", "docs_only", "unknown") and not c.is_model_baseline)
        for c in candidates):
        reasons.append("all candidates are dataset/docs/empty repos")
    if comparable < 2:
        reasons.append(f"only {comparable} comparable model(s) (need >=2)")
    if any(c.is_model_baseline and not c.matches_task_domain for c in candidates):
        reasons.append("baseline does not match seismic task domain")
    if any(c.is_model_baseline and c.reproducibility_score < 0.6 for c in candidates):
        reasons.append("repo reproducibility score below 0.6")
    return BaselineGateStatus(
        external_verified_model_baselines=ext_verified,
        comparable_count=comparable,
        run_gate_passed=comparable >= 1,
        research_gate_passed=ext_verified >= 1,
        insufficient_reasons=reasons,
        comparison_grade="research" if ext_verified >= 1 else "degraded",
    )
```
Add step methods:
```python
    async def _evaluate_baseline_gate(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped baseline gate (non-seismic)."
            return
        run.baseline_gate_status = _baseline_gate_status(run.baseline_candidates)
        g = run.baseline_gate_status
        if run.steps:
            run.steps[-1].summary = (
                f"Baseline gate: {g.comparison_grade} "
                f"(verified={g.external_verified_model_baselines}, "
                f"comparable={g.comparable_count}).")

    async def _re_search_literature(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped re-search (non-seismic)."
            return
        # Focused queries (escalate specificity by round).
        queries = [
            "seismic event classification deep learning github",
            "earthquake explosion CNN waveform code reproduction",
            "EQTransformer PhaseNet seismic waveform reproduction",
        ]
        round_idx = min(run.re_search_round, len(queries) - 1)
        new_papers = await self.literature_router.search(
            [queries[round_idx]], max_papers=run.constraints.max_papers,
            enable_semantic_scholar=run.constraints.enable_semantic_scholar,
            enable_arxiv=run.constraints.enable_arxiv, domain=run.domain,
        )
        # Replace dataset/no-code/non-eligible papers; keep method_model.
        keep = [p for p in run.papers if p.baseline_eligible]
        replaced = len(run.papers) - len(keep)
        run.papers = keep + new_papers
        run.evidence_changed = replaced > 0 or len(new_papers) > 0
        run.re_search_round += 1
        if run.steps:
            run.steps[-1].summary = (
                f"Re-search round {run.re_search_round}: replaced {replaced} non-eligible papers, "
                f"added {len(new_papers)} new; evidence_changed={run.evidence_changed}.")
```
In `backend/app/tools/literature_router.py` line 54, change:
```python
        per_source_limit = max(max_papers + 2, 8)
```
(was `max(1, min(max_papers, max_papers // len(sources) + 1))`.)

- [ ] **Step 4: Run tests to verify they pass + literature_router regression**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_baseline_gate.py tests/test_re_search_literature.py tests/test_literature_router.py -v`
Expected: PASS (incl. existing literature_router tests — the `per_source_limit` change gives a bigger candidate pool; verify the existing `test_literature_router_merges_sources_and_deduplicates` still asserts the same top papers. If a test asserts `last_source_stats` counts that change with the new limit, update the assertion to match the new per-source counts — but do NOT weaken the ranking assertions.)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 4: CodeWriter `macro` mode

**Files:**
- Modify: `backend/app/agents/code_writer_agent.py`
- Test: `backend/tests/test_code_writer_macro.py`

**Interfaces:**
- `CodeWriterAgent.arun("macro", hypothesis, experiment_plan, *, current_source, last_metrics, last_comparison, notes, run_id) -> str`。Prompt：从 metrics 诊断 + 用不同架构重写 model.py。Fallback：`FALLBACK_MODEL_PY`（同 initial/repair）。

- [ ] **Step 1: Write the failing test**

```python
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
    assert a.requests[0].agent == "code_writer"
    # macro prompt must surface the metrics so the LLM can diagnose
    assert "0.4" in a.requests[0].user


@pytest.mark.asyncio
async def test_macro_mode_falls_back_on_garbage() -> None:
    a = CodeWriterAgent(FakeLLM("garbage"))
    out = await a.arun("macro", _hyp(), _plan(), current_source="x",
                       last_metrics={"accuracy": 0.3}, last_comparison={}, notes=[], run_id="r")
    assert out == FALLBACK_MODEL_PY
```

- [ ] **Step 2: Run test to verify it fail**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_code_writer_macro.py -v`
Expected: FAIL (macro mode not supported)

- [ ] **Step 3: Implement**

In `backend/app/agents/code_writer_agent.py`:
- Add `MACRO_TEMPLATE`:
```python
MACRO_TEMPLATE = """The previous model.py ran but performed poorly. Current source:
```python
{current_source}
```

Last metrics (method): {last_metrics}
Comparison: {last_comparison}
Notes: {notes}

The model is not a crash (tests pass) but the result is bad. Rewrite model.py with a
DIFFERENT architecture/approach to improve the metric (e.g. different feature extractor,
different classifier, multi-channel aggregation). Keep the SeismicModel class with
fit()/predict(). Return a single ```python block```."""
```
- Extend `arun` to handle `mode == "macro"` (accept `last_metrics`/`last_comparison`/`notes` kwargs). Use `MACRO_TEMPLATE`. Keep `response_format=LLMResponseFormat.text` + `_CodeExtractor(FALLBACK_MODEL_PY)`. The `mode` Literal becomes `"initial" | "repair" | "macro"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_code_writer_macro.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 5: Macro-ReAct step + `_execute_micro_loop` 重构 + switchback

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py` — 抽 `_execute_micro_loop`；`_run_code_experiment` 读 `code_experiment_mode`；新 `_run_macro_react` step。
- Test: `backend/tests/test_macro_react.py`

**Interfaces:**
- `_execute_micro_loop(self, run, starting_source, hypothesis, trigger) -> CodeExperimentResult`：S4 micro 闭环核心（CodeWriter 不再在 step 内调，starting_source 由 caller 传）。
- `_run_code_experiment(run)` step：读 `run.code_experiment_mode`：`initial`→CodeWriter(initial)→`_execute_micro_loop`；`macro`→读上一个 `run.code_experiment` 的 metrics→CodeWriter(macro)→`_execute_micro_loop`；`switchback`→选 Top2→CodeWriter(initial with Top2)→`_execute_micro_loop`。设 `trigger` + 存 `run.code_experiment`。
- `_run_macro_react(run)` step：读 `run.code_experiment.summary`，按触发条件设 `run.code_experiment_mode` + `macro_round`/`switchback_used`。**不重跑**——只决策，路由由 LangGraph 接管。

- [ ] **Step 1: Write the failing test (4 scenarios)**

```python
# backend/tests/test_macro_react.py
import pytest

from app.config import Settings
from app.schemas.code_experiment import CodeExperimentResult, ComparisonResult, ExperimentSummary
from app.schemas.run import ResearchConstraints, ResearchRun
from app.schemas.arena import HypothesisArenaResult
from app.workflows.scientist_workflow import ScientistWorkflow


def _ce(outcome, method_acc=0.4, baseline_acc=0.9) -> CodeExperimentResult:
    return CodeExperimentResult(
        trigger="initial",
        comparison=ComparisonResult(outcome=outcome, method_beats_baseline=(method_acc > baseline_acc),
                                    method_metrics={"accuracy": method_acc},
                                    baseline_metrics={"accuracy": baseline_acc}),
        summary=ExperimentSummary(outcome=outcome, method_beats_baseline=(method_acc > baseline_acc),
                                   best_metric=method_acc, tests_pass=True),
    )


def _run_with_code_exp(ce, switchback_id=None):
    r = ResearchRun(domain="seismic_event_classification", question="q",
                    constraints=ResearchConstraints(), mode="discovery")
    r.code_experiment = ce
    r.arena_result = HypothesisArenaResult(arena_id="a", mode="discovery",
                                           arena_level="simplified_ranking", candidates=[],
                                           ranking=[], selected_for_experiment="H1",
                                           switchback_candidate=switchback_id, ablation_design=[])
    return r


def _wf():
    return ScientistWorkflow(Settings(dashscope_api_key="", max_papers=2))


@pytest.mark.asyncio
async def test_macro_positive_accepted_no_macro():
    wf = _wf()
    r = _run_with_code_exp(_ce("completed_positive", 0.9, 0.5))
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None  # accept, no escalation
    assert r.macro_round == 0


@pytest.mark.asyncio
async def test_macro_failed_triggers_macro_round_1():
    wf = _wf()
    r = _run_with_code_exp(_ce("failed"))
    await wf._run_macro_react(r)
    assert r.code_experiment_mode == "macro"
    assert r.macro_round == 1


@pytest.mark.asyncio
async def test_macro_big_margin_negative_triggers_macro():
    wf = _wf()
    r = _run_with_code_exp(_ce("completed_negative", method_acc=0.3, baseline_acc=0.9))  # margin 0.6
    await wf._run_macro_react(r)
    assert r.code_experiment_mode == "macro"
    assert r.macro_round == 1


@pytest.mark.asyncio
async def test_macro_narrow_negative_accepted():
    wf = _wf()
    r = _run_with_code_exp(_ce("completed_negative", method_acc=0.86, baseline_acc=0.9))  # margin 0.04 < 0.05
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None  # narrow negative (<0.05) accepted, no macro


@pytest.mark.asyncio
async def test_macro_after_cap_switchback_to_top2():
    wf = _wf()
    r = _run_with_code_exp(_ce("failed"))
    r.macro_round = 1  # macro already used
    await wf._run_macro_react(r)
    assert r.code_experiment_mode == "switchback"
    assert r.switchback_used is True


@pytest.mark.asyncio
async def test_macro_no_top2_accepts_negative():
    wf = _wf()
    r = _run_with_code_exp(_ce("failed"), switchback_id=None)
    r.macro_round = 1
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None  # accept negative, no further escalation


@pytest.mark.asyncio
async def test_macro_non_seismic_noop():
    wf = _wf()
    r = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None
    assert r.macro_round == 0
```

> Note on the margin test: define "bad" as `outcome=="failed" OR (outcome=="completed_negative" AND (baseline_metric - method_metric) > 0.05)`. Use strict `>` so margin==0.05 is accepted (narrow). Adjust the `test_macro_narrow_negative_accepted` to use margin 0.049 if strict `>` makes 0.05 trigger — pick the boundary so the test reflects the rule. The implementer: make the boundary consistent with the assertion.

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_macro_react.py -v`
Expected: FAIL (no `_run_macro_react` / no `_execute_micro_loop`)

- [ ] **Step 3: Implement**

In `backend/app/workflows/scientist_workflow.py`:
- Refactor `_run_code_experiment` to extract `_execute_micro_loop(self, run, starting_source, hypothesis, trigger) -> CodeExperimentResult` (the S4 micro loop body: prepare sandbox → tests max 3 → train → build CodeExperimentResult with `trigger=trigger`). Keep the same logic (tests-fail skip train, train-crash failed, structured summary).
- `_run_code_experiment` step reads `run.code_experiment_mode`:
  - `None` or `"initial"`: `source = await self.code_writer.arun("initial", selected, run.experiment_plan, run_id=...)`; `trigger="initial"`.
  - `"macro"`: read previous `run.code_experiment` metrics → `source = await self.code_writer.arun("macro", selected, run.experiment_plan, current_source=run.code_experiment.model_py_source, last_metrics=..., last_comparison=..., notes=..., run_id=...)`; `trigger="macro"`.
  - `"switchback"`: select Top2 (`run.arena_result.switchback_candidate` → find in `run.hypotheses`, mark selected, Top1 unselected) → `source = await self.code_writer.arun("initial", top2, run.experiment_plan, run_id=...)`; `trigger="switchback"`.
  - Then `run.code_experiment = await self._execute_micro_loop(run, source, selected, trigger)`. Reset `run.code_experiment_mode = None` after running (so macro_react re-evaluates fresh).
- `_run_macro_react(run)` step (decision only — does NOT re-run the loop):
```python
    async def _run_macro_react(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps: run.steps[-1].summary = "Skipped macro-react (non-seismic)."
            return
        run.code_experiment_mode = None  # default: accept
        ce = run.code_experiment
        if ce is None:
            if run.steps: run.steps[-1].summary = "Macro-react: no code experiment to evaluate."
            return
        outcome = ce.summary.outcome
        method = ce.summary.best_metric
        baseline = _baseline_metric(ce)
        margin = (baseline - method) if (method is not None and baseline is not None) else None
        bad = (outcome == "failed") or (
            outcome == "completed_negative" and margin is not None and margin >= 0.05)
        if not bad:
            if run.steps: run.steps[-1].summary = f"Macro-react: accept ({outcome})."
            return
        # escalate
        if run.macro_round < 1:
            run.macro_round += 1
            run.code_experiment_mode = "macro"
            if run.steps: run.steps[-1].summary = "Macro-react: macro repair (round 1)."
            return
        if not run.switchback_used and run.arena_result and run.arena_result.switchback_candidate:
            run.switchback_used = True
            run.code_experiment_mode = "switchback"
            if run.steps: run.steps[-1].summary = "Macro-react: switchback to Top2."
            return
        if run.steps: run.steps[-1].summary = "Macro-react: accept negative result (no further escalation)."
```
- Module-level helpers `_baseline_metric(ce) -> float | None` (reads `comparison.baseline_metrics.accuracy`/`macro_f1`) — symmetric to the existing `_best_metric`.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_macro_react.py tests/test_code_experiment_loop.py -v`
Expected: PASS (the S4 loop test must still pass after the `_execute_micro_loop` refactor — it tests `_run_code_experiment` with FakeCodeWriter/FakeSandbox; verify the refactor didn't break it. If the S4 test set `run.code_experiment_mode`, leave it None for the initial path.)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 6: Novelty step + LangGraph novelty cycle (+ hypothesis_agent avoid_prior_art)

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py` — `_run_novelty_check` step + `_route_after_novelty`。
- Modify: `backend/app/agents/hypothesis_agent.py` — `avoid_prior_art: list[str] | None` 参数 + prompt 注入。
- Modify: `backend/app/agents/hypothesis_arena_agent.py` — `_discovery` 传 `run.novelty_verdict.prior_art_paper_ids`（若已存在）给 hypothesis_agent。
- Modify: `backend/app/workflows/langgraph_workflow.py` — `novelty_check` 节点 + `arena → novelty_check → _route_after_novelty` + `novelty_check → extract_code_urls`（非 already_done）或 `→ arena`（already_done + cap<2）。
- Test: `backend/tests/test_s5_langgraph_cycles.py`（novelty cycle 部分）

**Interfaces:**
- `_run_novelty_check(run)` step：调 NoveltyCheckerAgent（扩）→ 存 `run.novelty_verdict`；transfer/similar→RevisionAgent 应用 claim_revision；already_done→`prior_art_paper_ids` 加进 baseline 候选（dual effect）+ `novelty_round++`；novel/dataset_only→`novelty_status="ok"`；cap 后仍 already_done→`novelty_status="low_novelty"`。
- `_route_after_novelty(state)`：already_done 且 `novelty_round<2` → `arena`（重生成）；否则 `extract_code_urls`。

- [ ] **Step 1: Write the failing test (novelty cycle)**

```python
# backend/tests/test_s5_langgraph_cycles.py
import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.schemas.feedback_loop import NoveltyVerdict
from app.workflows.langgraph_workflow import LangGraphWorkflow


async def _noop_step(self, run): return None


def _stub(monkeypatch, methods):
    for m in methods:
        monkeypatch.setattr(LangGraphWorkflow, m, _noop_step)


@pytest.mark.asyncio
async def test_novelty_already_done_routes_back_to_arena_under_cap(monkeypatch):
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    _stub(monkeypatch, ["_plan", "_search_literature_with_langchain_tools",
        "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
        "_classify_papers", "_profile_scientific_data", "_extract_code_urls",
        "_discover_baselines_auto", "_verify_baselines_auto", "_evaluate_baseline_gate",
        "_design_experiment", "_run_code_experiment", "_run_macro_react", "_write_report",
        "_verify_claims", "_revise_report_after_audit", "_translate_report", "_route_intent"])
    # _run_arena + _run_novelty_check are real-ish (stubbed to set state):
    async def fake_arena(self, run):
        run.arena_result = None  # minimal
        run.novelty_round = getattr(run, "novelty_round", 0)
    async def fake_novelty(self, run):
        run.novelty_verdict = NoveltyVerdict(verdict="already_done", prior_art_paper_ids=["p1"])
        run.novelty_round += 1
    monkeypatch.setattr(LangGraphWorkflow, "_run_arena", fake_arena)
    monkeypatch.setattr(LangGraphWorkflow, "_run_novelty_check", fake_novelty)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf.run(run)
    # novelty_round incremented (at least one already_done → regen attempted)
    assert run.novelty_round >= 1
    # cap enforced: novelty_round <= 2
    assert run.novelty_round <= 2
    names = [s.name for s in run.steps if s.status == "completed"]
    assert "novelty_check" in names
    assert names.index("novelty_check") > names.index("arena")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s5_langgraph_cycles.py -v`
Expected: FAIL (no novelty_check node / routing)

- [ ] **Step 3: Implement**

In `backend/app/agents/hypothesis_agent.py`: add `avoid_prior_art: list[str] | None = None` param to `arun`; if provided, inject into the user prompt: "Avoid these already-done prior-art directions: {avoid_prior_art}. Generate a hypothesis in a different direction."

In `backend/app/agents/hypothesis_arena_agent.py` `_discovery`: pass `avoid_prior_art` from the existing `run.novelty_verdict.prior_art_paper_ids` (map paper_ids → titles via `run.papers`) to `hypothesis_agent.arun`.

In `backend/app/workflows/scientist_workflow.py`, add:
```python
    async def _run_novelty_check(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps: run.steps[-1].summary = "Skipped novelty check (non-seismic)."
            return
        selected = _selected_hypothesis(run.hypotheses)
        verdict = await self.novelty_checker.arun(
            run.papers, selected, run.idea_brief, run_id=run.run_id)
        run.novelty_verdict = verdict
        if verdict.verdict in ("transfer_applicability", "similar_work") and verdict.claim_revision:
            self.revision.run(run.hypotheses, novelty_verdict=verdict)
        if verdict.verdict == "already_done":
            # dual effect: prior-art papers become baseline candidates
            for pid in verdict.prior_art_paper_ids:
                if not any(c.paper_id == pid for c in run.baseline_candidates):
                    run.baseline_candidates.append(_prior_art_as_candidate(pid, run.papers))
            run.novelty_round += 1
            if run.novelty_round >= 2:
                run.novelty_status = "low_novelty"
        else:
            run.novelty_status = "ok"
        if run.steps:
            run.steps[-1].summary = (
                f"Novelty: {verdict.verdict} (round {run.novelty_round}, status={run.novelty_status}).")

    def _route_after_novelty(self, state) -> str:
        run = state["run"]
        if run.domain != "seismic_event_classification":
            return "extract_code_urls"  # shouldn't be reached (non-seismic skips this node)
        v = run.novelty_verdict
        if v and v.verdict == "already_done" and run.novelty_round < 2:
            return "arena"
        return "extract_code_urls"
```
(`_prior_art_as_candidate(pid, papers) -> BaselineCandidate`: build a candidate from the prior-art paper's `code_url` if any; reuse `baseline_discovery_agent._candidate_from_paper_code_url` if the paper has code_url, else a minimal placeholder candidate with `paper_id=pid`, `code_source="prior_art"`, `is_model_baseline=False`, `repo_type="unknown"` — the verifier will judge it next pass. Keep it minimal.)

In `backend/app/workflows/langgraph_workflow.py` `_build_graph`:
- Add node: `graph.add_node("novelty_check", self._make_step_node("novelty_check", "_run_novelty_check"))`.
- Replace edge `arena → extract_code_urls` with `arena → novelty_check` + conditional `novelty_check → _route_after_novelty → {arena, extract_code_urls}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s5_langgraph_cycles.py -v`
Expected: PASS (novelty cycle routes back to arena under cap)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 7: LangGraph baseline-gate + re-search cycle

**Files:**
- Modify: `backend/app/workflows/langgraph_workflow.py` — `baseline_quality_gate` + `re_search_literature` 节点 + routing。
- Modify: `backend/app/workflows/scientist_workflow.py` — `_route_after_gate` + `_route_after_research`。
- Test: `backend/tests/test_s5_langgraph_cycles.py`（append baseline cycle tests）

**Interfaces:**
- `_route_after_gate(state)`: seismic + research fail + `re_search_round<2` → `re_search_literature`；否则 `experiment_design`。
- `_route_after_research(state)`: `evidence_changed` → `evidence_ledger`（全链重跑）；否则 `baseline_discover`。
- 节点：`baseline_verify → baseline_quality_gate → _route_after_gate → {re_search_literature, experiment_design}`；`re_search_literature → _route_after_research → {evidence_ledger, baseline_discover}`。

- [ ] **Step 1: Append failing tests (baseline cycle)**

```python
# append to backend/tests/test_s5_langgraph_cycles.py
@pytest.mark.asyncio
async def test_baseline_gate_degraded_after_cap_routes_to_experiment_design(monkeypatch):
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    _stub(monkeypatch, ["_plan", "_search_literature_with_langchain_tools",
        "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
        "_classify_papers", "_profile_scientific_data", "_run_arena", "_run_novelty_check",
        "_extract_code_urls", "_discover_baselines_auto", "_verify_baselines_auto",
        "_design_experiment", "_run_code_experiment", "_run_macro_react", "_write_report",
        "_verify_claims", "_revise_report_after_audit", "_translate_report", "_route_intent"])
    async def fake_gate(self, run):
        from app.schemas.feedback_loop import BaselineGateStatus
        run.baseline_gate_status = BaselineGateStatus(research_gate_passed=False, comparison_grade="degraded")
        run.re_search_round = 2  # cap reached
    monkeypatch.setattr(LangGraphWorkflow, "_evaluate_baseline_gate", fake_gate)
    async def fake_research(self, run): raise AssertionError("should not re-search at cap")
    monkeypatch.setattr(LangGraphWorkflow, "_re_search_literature", fake_research)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf.run(run)
    names = [s.name for s in run.steps if s.status == "completed"]
    assert "baseline_quality_gate" in names
    assert "experiment_design" in names
    # re_search NOT in steps (cap reached, degraded -> experiment_design)
    assert "re_search_literature" not in names


@pytest.mark.asyncio
async def test_research_evidence_changed_routes_to_evidence_ledger(monkeypatch):
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    _stub(monkeypatch, ["_plan", "_search_literature_with_langchain_tools",
        "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
        "_classify_papers", "_profile_scientific_data", "_run_arena", "_run_novelty_check",
        "_extract_code_urls", "_discover_baselines_auto", "_verify_baselines_auto",
        "_design_experiment", "_run_code_experiment", "_run_macro_react", "_write_report",
        "_verify_claims", "_revise_report_after_audit", "_translate_report", "_route_intent"])
    async def fake_gate(self, run):
        from app.schemas.feedback_loop import BaselineGateStatus
        run.baseline_gate_status = BaselineGateStatus(research_gate_passed=False)
    monkeypatch.setattr(LangGraphWorkflow, "_evaluate_baseline_gate", fake_gate)
    async def fake_research(self, run):
        run.evidence_changed = True
        run.re_search_round += 1
    monkeypatch.setattr(LangGraphWorkflow, "_re_search_literature", fake_research)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf.run(run)
    names = [s.name for s in run.steps if s.status == "completed"]
    assert "re_search_literature" in names
    # evidence_ledger re-run (appears after re_search in step order)
    assert names.index("evidence_ledger") > names.index("re_search_literature")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s5_langgraph_cycles.py -v`
Expected: FAIL (no baseline_quality_gate/re_search nodes)

- [ ] **Step 3: Implement**

In `backend/app/workflows/scientist_workflow.py`, add routing:
```python
    def _route_after_gate(self, state) -> str:
        run = state["run"]
        if run.domain != "seismic_event_classification":
            return "experiment_design"
        g = run.baseline_gate_status
        if g and not g.research_gate_passed and run.re_search_round < 2:
            return "re_search_literature"
        return "experiment_design"

    def _route_after_research(self, state) -> str:
        run = state["run"]
        return "evidence_ledger" if run.evidence_changed else "baseline_discover"
```
In `backend/app/workflows/langgraph_workflow.py` `_build_graph`:
- Add nodes: `graph.add_node("baseline_quality_gate", self._make_step_node("baseline_quality_gate", "_evaluate_baseline_gate"))`; `graph.add_node("re_search_literature", self._make_step_node("re_search_literature", "_re_search_literature"))`.
- Replace edge `baseline_verify → experiment_design` with `baseline_verify → baseline_quality_gate` + conditional `baseline_quality_gate → _route_after_gate → {re_search_literature, experiment_design}` + conditional `re_search_literature → _route_after_research → {evidence_ledger, baseline_discover}`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s5_langgraph_cycles.py -v`
Expected: PASS

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 8: LangGraph macro cycle

**Files:**
- Modify: `backend/app/workflows/langgraph_workflow.py` — `macro_react` 节点 + `code_experiment → macro_react → _route_after_macro → {code_experiment, report_writer}`。
- Modify: `backend/app/workflows/scientist_workflow.py` — `_route_after_macro`。
- Test: `backend/tests/test_s5_langgraph_cycles.py`（append macro cycle test）

**Interfaces:**
- `_route_after_macro(state)`: positive / 窄负 → `report_writer`；bad + `macro_round<1` → `code_experiment`（mode=macro）；bad + cap + Top2 → `code_experiment`（mode=switchback）；否则 `report_writer`（negative）。

- [ ] **Step 1: Append failing test (macro cycle)**

```python
# append to backend/tests/test_s5_langgraph_cycles.py
@pytest.mark.asyncio
async def test_macro_failed_routes_to_code_experiment_then_report(monkeypatch):
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    _stub(monkeypatch, [...])
    call_count = {"ce": 0}
    async def fake_ce(self, run):
        call_count["ce"] += 1
        from app.schemas.code_experiment import CodeExperimentResult, ComparisonResult, ExperimentSummary
        if call_count["ce"] == 1:
            run.code_experiment = CodeExperimentResult(trigger="initial",
                comparison=ComparisonResult(outcome="failed"),
                summary=ExperimentSummary(outcome="failed", tests_pass=False))
        else:
            run.code_experiment = CodeExperimentResult(trigger="macro",
                comparison=ComparisonResult(outcome="completed_positive", method_beats_baseline=True,
                                            method_metrics={"accuracy":0.9}, baseline_metrics={"accuracy":0.5}),
                summary=ExperimentSummary(outcome="completed_positive", method_beats_baseline=True, best_metric=0.9))
        run.code_experiment_mode = None
    monkeypatch.setattr(LangGraphWorkflow, "_run_code_experiment", fake_ce)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf.run(run)
    assert call_count["ce"] == 2  # initial + macro
    assert run.macro_round == 1
    names = [s.name for s in run.steps if s.status == "completed"]
    assert "macro_react" in names
    assert names.index("macro_react") > names.index("code_experiment")
```

- [ ] **Step 2: Run test to verify it fail**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s5_langgraph_cycles.py -v`
Expected: FAIL (no macro_react node)

- [ ] **Step 3: Implement**

In `backend/app/workflows/scientist_workflow.py`, add the routing function (single decision point: `_run_macro_react` sets `run.code_experiment_mode` when it decides to loop; the route just honors it):
```python
    def _route_after_macro(self, state) -> str:
        run = state["run"]
        # macro_react already decided: mode is None -> accept (report_writer);
        # mode in {"macro","switchback"} -> re-run code_experiment.
        if run.domain != "seismic_event_classification":
            return "report_writer"
        return "code_experiment" if run.code_experiment_mode is not None else "report_writer"
```
> The full flow: `code_experiment` (reads `code_experiment_mode` set by the previous `macro_react`; runs the micro loop; **resets `run.code_experiment_mode = None`** at the end so the next `macro_react` evaluates fresh) → `macro_react` (reads the fresh `code_experiment` result; if bad and `macro_round<1` → increment `macro_round`, set `mode="macro"`; elif bad and `!switchback_used` and Top2 exists → set `switchback_used=True`, `mode="switchback"`; else leave `mode=None` → accept negative) → `_route_after_macro` (`mode is not None` → `code_experiment` loop; else `report_writer`). Counters increment in `macro_react`, never reset (§1 inner-cap rule).

In `backend/app/workflows/langgraph_workflow.py` `_build_graph`:
- Add node: `graph.add_node("macro_react", self._make_step_node("macro_react", "_run_macro_react"))`.
- Replace edge `code_experiment → report_writer` with `code_experiment → macro_react` + conditional `macro_react → _route_after_macro → {code_experiment, report_writer}`.

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s5_langgraph_cycles.py tests/test_langgraph_workflow.py -v`
Expected: PASS (S5 cycles + existing non-seismic langgraph test — non-seismic step_names unchanged since S5 nodes are in seismic-only conditional branches)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 9: Classic `_run_after_evidence_review` 线性透传

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py` — `_run_after_evidence_review` 插入 novelty_check / baseline_gate / macro_react（线性，无 loop）。
- Test: `backend/tests/test_workflow_classic_s5.py`

**Interfaces:**
- classic seismic 分支：`... → arena → novelty_check → extract_code_urls → baseline_discover → baseline_verify → baseline_quality_gate → experiment_design → code_experiment → macro_react → report_writer`（单遍，无 cycle back）。非 seismic 不变。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_workflow_classic_s5.py
import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


async def _noop(self, run): return None


@pytest.mark.asyncio
async def test_classic_seismic_runs_new_steps_linearly(monkeypatch, tmp_path):
    wf = ScientistWorkflow(Settings(dashscope_api_key="", max_papers=2))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    for m in ("_plan", "_search_literature", "_verify_citations", "_build_evidence",
              "_mine_literature", "_classify_papers", "_profile_scientific_data", "_run_arena",
              "_run_novelty_check", "_extract_code_urls", "_discover_baselines_auto",
              "_verify_baselines_auto", "_evaluate_baseline_gate", "_design_experiment",
              "_run_code_experiment", "_run_macro_react", "_write_report", "_verify_claims",
              "_revise_report_after_audit", "_translate_report", "_route_intent"):
        monkeypatch.setattr(ScientistWorkflow, m, _noop, raising=False)
    monkeypatch.setattr(wf.literature_router, "search", _noop)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf._run_after_evidence_review(run)
    names = [s.name for s in run.steps if s.status == "completed"]
    # new steps present in order, no loop back
    assert "novelty_check" in names and names.index("novelty_check") > names.index("arena")
    assert "baseline_quality_gate" in names and names.index("baseline_quality_gate") > names.index("baseline_verify")
    assert "macro_react" in names and names.index("macro_react") > names.index("code_experiment")
    # no re_search loop in classic single-pass
    assert "re_search_literature" not in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_workflow_classic_s5.py -v`
Expected: FAIL (new steps not inserted in classic chain)

- [ ] **Step 3: Implement**

In `backend/app/workflows/scientist_workflow.py` `_run_after_evidence_review`, update the seismic branch:
```python
        if run.domain == "seismic_event_classification":
            await self._step(run, "arena", self._run_arena)
            await self._step(run, "novelty_check", self._run_novelty_check)
            await self._step(run, "extract_code_urls", self._extract_code_urls)
            await self._step(run, "baseline_discover", self._discover_baselines_auto)
            await self._step(run, "baseline_verify", self._verify_baselines_auto)
            await self._step(run, "baseline_quality_gate", self._evaluate_baseline_gate)
        else:
            await self._step(run, "hypothesis_debate", self._generate_and_critique)
        await self._step(run, "experiment_design", self._design_experiment)
        if run.domain == "seismic_event_classification":
            await self._step(run, "code_experiment", self._run_code_experiment)
            await self._step(run, "macro_react", self._run_macro_react)
        await self._step(run, "report_writer", self._write_report)
        # ... rest unchanged (claim_verification, report_revision, ...)
```
(No re_search_literature in classic single-pass — the classic engine runs baseline_quality_gate once; if it fails, it does NOT loop. Full loop behavior is LangGraph-only per the design.)

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_workflow_classic_s5.py -v`
Expected: PASS

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 10: Feedback Loop Panel（前端）

**Files:**
- Modify: `frontend/lib/api.ts` — `NoveltyVerdict`/`BaselineGateStatus` 类型 + `Run` 新字段。
- Create: `frontend/components/workbench/FeedbackLoopPanel.tsx`
- Modify: `frontend/components/workbench/Workbench.tsx` — seismic 挂 FeedbackLoopPanel。
- Test: manual + `npx tsc --noEmit`.

- [ ] **Step 1: Add types to `frontend/lib/api.ts`**

```typescript
export interface NoveltyVerdict {
  verdict: "novel" | "transfer_applicability" | "already_done" | "dataset_only" | "similar_work";
  claim_revision?: string | null;
  prior_art_paper_ids: string[];
  overlap_points: string[];
  retainable_novelty: string[];
  reasoning: string;
  similar_work: Record<string, unknown>[];
  has_public_code: boolean;
}
export interface BaselineGateStatus {
  external_verified_model_baselines: number;
  comparable_count: number;
  run_gate_passed: boolean;
  research_gate_passed: boolean;
  insufficient_reasons: string[];
  comparison_grade: "research" | "degraded";
}
```
Add to `Run`:
```typescript
  novelty_verdict?: NoveltyVerdict | null;
  novelty_status?: "not_checked" | "ok" | "low_novelty";
  novelty_round?: number;
  baseline_gate_status?: BaselineGateStatus | null;
  re_search_round?: number;
  evidence_changed?: boolean;
  hypothesis_changed?: boolean;
  baseline_changed?: boolean;
  macro_round?: number;
  switchback_used?: boolean;
  code_experiment_mode?: string | null;
```

- [ ] **Step 2: FeedbackLoopPanel**

```tsx
// frontend/components/workbench/FeedbackLoopPanel.tsx
import type { Run } from "../../lib/api";

const VERDICT_BADGE: Record<string, string> = {
  novel: "good", transfer_applicability: "warn", already_done: "warn",
  dataset_only: "good", similar_work: "warn",
};

export function FeedbackLoopPanel({ run }: { run: Run }) {
  const v = run.novelty_verdict;
  const g = run.baseline_gate_status;
  return (
    <section className="panel">
      <h3>Feedback Loop</h3>
      <div className="badges">
        {v && <span className={`badge ${VERDICT_BADGE[v.verdict] ?? "warn"}`}>novelty: {v.verdict}</span>}
        {run.novelty_status && run.novelty_status !== "not_checked" && (
          <span className={`badge ${run.novelty_status === "ok" ? "good" : "warn"}`}>{run.novelty_status}</span>
        )}
        {g && <span className={`badge ${g.comparison_grade === "research" ? "good" : "warn"}`}>{g.comparison_grade}</span>}
      </div>
      <ul className="kv">
        <li>novelty_round: {run.novelty_round ?? 0}</li>
        <li>re_search_round: {run.re_search_round ?? 0}</li>
        <li>macro_round: {run.macro_round ?? 0} · switchback: {String(run.switchback_used ?? false)}</li>
        <li>evidence_changed: {String(run.evidence_changed ?? false)} · hypothesis_changed: {String(run.hypothesis_changed ?? false)}</li>
      </ul>
      {g && g.insufficient_reasons.length > 0 && (
        <ul className="notes">{g.insufficient_reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
      )}
      {v && v.reasoning && <p className="muted">{v.reasoning}</p>}
    </section>
  );
}
```

- [ ] **Step 3: Wire into Workbench**

In `frontend/components/workbench/Workbench.tsx`, in the seismic layout (near ExperimentResultsPanel), add:
```tsx
{run && <FeedbackLoopPanel run={run} />}
```
(import `FeedbackLoopPanel` from `./FeedbackLoopPanel`.)

- [ ] **Step 4: Verify build**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npx tsc --noEmit`
Expected: exit 0.

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 11: 验收

- [ ] **Step 1: Full backend suite**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q
```
Expected: all green (was 183 after S4; S5 adds ~25-30 new tests). 非 seismic langgraph step_names 不变（S5 节点条件跳过）。

- [ ] **Step 2: Live acceptance (real Qwen, seismic discovery run, LangGraph)**

Seismic run end-to-end with `WORKFLOW_ENGINE=langgraph`:
1. `novelty_check` 在 `arena` 后出现；若 Top1 撞 prior art → `novelty_round` 递增、Arena 重生成（≤2 轮）或 `novelty_status=low_novelty` 继续。
2. `baseline_quality_gate` 在 `baseline_verify` 后；demo 大概率 0 verified → `comparison_grade=degraded`，重搜 2 轮仍 0 → 降级用 harness_trivial 跑。
3. `code_experiment` 跑完 → `macro_react` 评估；若 positive → report_writer；若 failed/big-margin → macro repair (1 轮) → 仍 bad → switchback Top2 (若有) → 仍 bad → negative。
4. 前端 FeedbackLoopPanel 显示 verdict/grade/rounds/dirty flags。
5. 诚实：demo 走 degraded + (可能) low_novelty 路径，闭环不死、报告诚实标记。

- [ ] **Step 3: Skip commit (local-only).** Update `SESSION_HANDOFF.md` §2/§5 标记 S5 完成。

---

## S5 验收

- [ ] 全量测试绿（新增 ~25-30 个 S5 测试 + per_source_limit 修不破现有 literature_router）。
- [ ] Live seismic run (LangGraph) 跑通三循环之一至少一次（novelty regen 或 re_search 或 macro），诚实分流 research/degraded/negative。
- [ ] 非 seismic 路径不受 S5 影响（step_names 不变）。

## 已知 S5 局限（留给后续）

- **§5.4 报告增强留 S5.5/S6**：Result Evaluator(pass/partial/fail)、Ablation Agent、Result Interpreter、v3 报告 provenance 字段（Baseline Provenance/Experiment Iteration Log/Code Debug Log/Arena Report/Ablation Report/Result Support Judgment）不在 S5 范围。
- **verified_repo baseline 分支留 S7**：S5 的 `comparison_grade=degraded` 是 demo 现实（0 verified）；S7 接真实 STEAD + 真实 repo 验证后才常触 `research` grade。
- **classic 引擎无 cycle**：完整反馈循环仅 LangGraph；classic 单遍透传，不重搜/不 macro/不 switchback。
- **macro cap=1 全局**：Top2 不享 macro 修复（防 p-hack + 爆炸）；v3 稳定后可调。
- **re_search cap=2**：v3 稳定后阈值可调（≥2 可比模型 = harness_trivial + ≥1 verified_repo 当前选择）。
- **novelty_check 依赖 LLM 判断**：有误判可能；前端标 reasoning + verdict 供人工核。
- **per_source_limit 修了截断**，但重搜质量仍受 GitHub 匿名限额/PwC 断网限制。
