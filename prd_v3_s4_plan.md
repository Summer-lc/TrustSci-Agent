# v3 Sprint S4 实施计划：Code Experiment Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Arena 选出的 Top1 假设真写成代码跑起来——固定 harness（numpy 合成波形 + sklearn）+ LLM 只写 `model.py`，micro ReAct（写→跑 tests→报错→修→重跑，max 3）闭环产出 metrics/comparison，诚实分流出 completed_positive / completed_negative / failed。

**Architecture:** LangGraph 链在 `experiment_design → report_writer` 之间插入 `code_experiment` 节点（seismic 跑代码实验，非 seismic no-op）。`code_experiment` = `ScientistWorkflow._run_code_experiment(run)`：`CodeWriterAgent`（LCEL，写/补 `model.py`，LLM 失智落骨架 fallback）→ `SandboxExecutor`（同容器 subprocess，白名单 `python tests.py`/`python train.py`，timeout）跑 `tests.py`（接口/shape/NaN/label 预检）→ 过则跑 `train.py` 出 `metrics.json`+`comparison.json`，不过或 train 崩 → failed。`FairComparisonPlanner`（确定性无 LLM）固定同 split/同 metric/同预处理。产物挂 `ResearchRun.code_experiment: CodeExperimentResult`。macro ReAct（评估→改架构→重跑）留 S5，S4 只 micro。

**Tech Stack:** Python 3.11 / FastAPI / Pydantic / LangChain LCEL / LangGraph StateGraph / numpy / scikit-learn（CPU，不加 torch/scipy）/ pytest / Next.js。

## Global Constraints

- **不 commit**：所有改动留本地工作区（每个 Task 的 Step 5 都是 "Skip commit (local-only)"）。
- 后端测试在 Docker dev 栈：`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest <path> -v`。容器 WORKDIR `/app`，`data/` 挂在 `/app/data`，`experiments/` 本 sprint 起挂在 `/app/experiments`（见 Task 1）。
- `WORKFLOW_ENGINE=langgraph`，真实 Qwen `qwen3.7-max`。agent 走 `LLMClientRunnable`+`build_agent_prompt`+`FallbackParser`，调 `QwenClient.complete()`，审计日志 `data/outputs/llm_calls/{run_id}.jsonl`。
- **S4 只对 `run.domain == "seismic_event_classification"` 启用代码实验**；非 seismic no-op（同 `paper_classification` 处理，节点在路径里但 no-op，非 seismic step_names 仍含 `code_experiment`）。
- **只 micro，无 macro**：micro cap=3 只覆盖 tests 阶段；tests 三轮不过 → `outcome=failed`、skip train；train 崩 → `outcome=failed`，不消耗 repair 轮（S4 v1 稳定优先）。macro ReAct 留 S5。
- **acceptance 与 outcome 分开**：`acceptance_gate`（tests_pass/metrics_generated/baseline_comparison_written/all_passed）是产物清单；`comparison.outcome`（completed_positive|completed_negative|failed）是实验裁决；`summary` 是结构化摘要（非自然语言）。三者正交。
- 基线 = harness 内置弱基线（每通道时域统计 + LogisticRegression），`baseline_source: harness_trivial`；接口预留 `verified_repo` 分支给 S7（S4 不实现）。
- harness 接口预留 `model_family: sklearn|torch`、`harness_version`、`max_repair_rounds`、`acceptance_gate`，torch CNN 留 S7 不推翻架构。
- YAGNI：schema/字段按 S4 需要建，不提前建 S5/S7 的。
- 合成波形纯 numpy 实现 Ricker/包络，**不引入 scipy**。依赖只加 `numpy`+`scikit-learn`。
- 文件路径相对仓库根 `d:/For work/TrustSci-Agent/`。

## File Structure

- **Create** `backend/app/schemas/code_experiment.py` — `CodeExperimentResult` 及子 schema。
- **Create** `backend/app/tools/sandbox_executor.py` — 受控 subprocess 执行器。
- **Create** `backend/app/agents/code_writer_agent.py` — LCEL 写/补 `model.py`，骨架 fallback。
- **Create** `backend/app/agents/fair_comparison_planner.py` — 确定性公平对比计划。
- **Create** `backend/tests/_s4_harness.py` — 测试用的 harness 模块加载器（importlib，walk-up 找 `experiments/seismic_event_classification/`）。
- **Create** `backend/tests/test_s4_schemas.py`
- **Create** `backend/tests/test_s4_harness_data.py`
- **Create** `backend/tests/test_s4_harness.py`（baseline/train/tests.py/manifest）
- **Create** `backend/tests/test_sandbox_executor.py`
- **Create** `backend/tests/test_code_writer_agent.py`
- **Create** `backend/tests/test_fair_comparison_planner.py`
- **Create** `backend/tests/test_code_experiment_loop.py`（4 场景：tests 过→positive / tests 三轮不过→failed / fallback 骨架→negative / train 崩→failed）
- **Create** `backend/tests/test_s4_langgraph.py`（seismic 才真跑 code_experiment）
- **Create** `experiments/seismic_event_classification/data.py` — numpy 确定性合成波形 + `load_split`。
- **Create** `experiments/seismic_event_classification/baseline.py` — 固定弱基线。
- **Create** `experiments/seismic_event_classification/train.py` — 训 baseline+method → `metrics.json`+`comparison.json`。
- **Create** `experiments/seismic_event_classification/tests.py` — acceptance gate 预检（import/interface/shape/NaN/label）。
- **Create** `experiments/seismic_event_classification/harness_manifest.json`
-（`experiments/seismic_event_classification/model.py` 不在仓库固定——由 CodeWriterAgent 运行时生成写入 sandbox；但提供一个 `model_template.py` 供 README/调试，非闭环依赖）
- **Create** `frontend/components/workbench/CodePlanPanel.tsx`
- **Create** `frontend/components/workbench/CodeDebugPanel.tsx`
- **Create** `frontend/components/workbench/ExperimentResultsPanel.tsx`
- **Modify** `backend/requirements.txt` — 加 `numpy`+`scikit-learn`。
- **Modify** `backend/Dockerfile` — `COPY experiments /app/experiments`。
- **Modify** `docker-compose.dev.yml` — backend volumes 加 `./experiments:/app/experiments`。
- **Modify** `backend/app/config.py` — 加 `experiments_dir`、`code_experiment_timeout_seconds`。
- **Modify** `backend/app/schemas/run.py` — 加 `code_experiment` 字段。
- **Modify** `backend/app/workflows/scientist_workflow.py` — 加 `_run_code_experiment` step + 在 `_run_after_evidence_review` seismic 分支插入；`__init__` 装 code_writer/fair_comparison_planner/sandbox_executor。
- **Modify** `backend/app/workflows/langgraph_workflow.py` — 加 `code_experiment` 节点 + 改 `experiment_design → report_writer` 边为 `experiment_design → code_experiment → report_writer`；更新非 seismic step_names 断言。
- **Modify** `frontend/lib/api.ts` — 加 `CodeExperimentResult` 类型 + `run.code_experiment`。
- **Modify** `frontend/components/workbench/Workbench.tsx` — seismic 布局挂 3 个新面板。

---

### Task 1: 依赖 + docker 挂载 + Settings + schema

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/Dockerfile`
- Modify: `docker-compose.dev.yml`
- Modify: `backend/app/config.py`
- Create: `backend/app/schemas/code_experiment.py`
- Modify: `backend/app/schemas/run.py`
- Test: `backend/tests/test_s4_schemas.py`

**Interfaces:**
- Produces: `CodeExperimentResult`/`AcceptanceGate`/`ComparisonResult`/`FairComparisonPlan`/`IterEntry`/`DebugEntry`/`ExperimentSummary` schema；`ResearchRun.code_experiment` 字段；`Settings.experiments_dir`、`Settings.code_experiment_timeout_seconds`。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_s4_schemas.py
from app.config import Settings
from app.schemas.code_experiment import (
    CodeExperimentResult, AcceptanceGate, ComparisonResult, FairComparisonPlan,
    IterEntry, DebugEntry, ExperimentSummary,
)
from app.schemas.run import ResearchRun, ResearchConstraints


def test_code_experiment_result_defaults() -> None:
    r = CodeExperimentResult()
    assert r.harness_version == "seismic_sklearn_v1"
    assert r.model_family == "sklearn"
    assert r.baseline_source == "harness_trivial"
    assert r.model_py_source == ""
    assert isinstance(r.fair_comparison_plan, FairComparisonPlan)
    assert isinstance(r.acceptance_gate, AcceptanceGate)
    assert isinstance(r.comparison, ComparisonResult)
    assert r.iteration_log == [] and r.debug_log == []
    assert isinstance(r.summary, ExperimentSummary)


def test_acceptance_gate_all_passed() -> None:
    g = AcceptanceGate()
    assert g.all_passed is False
    g2 = AcceptanceGate(tests_pass=True, metrics_generated=True, baseline_comparison_written=True)
    assert g2.all_passed is True


def test_comparison_outcome_literal() -> None:
    c = ComparisonResult(outcome="completed_positive", method_beats_baseline=True)
    assert c.outcome == "completed_positive"
    c2 = ComparisonResult()
    assert c2.outcome == "failed"  # default
    assert c2.method_beats_baseline is False


def test_experiment_summary_structured() -> None:
    s = ExperimentSummary()
    assert s.outcome == "failed"
    assert s.tests_pass is False
    assert s.method_beats_baseline is False
    assert s.baseline_source == "harness_trivial"
    assert s.best_metric is None
    assert s.failure_reason is None


def test_run_has_code_experiment_field() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints())
    assert run.code_experiment is None


def test_settings_experiments_dir_and_timeout() -> None:
    s = Settings(dashscope_api_key="")
    assert str(s.experiments_dir) == "experiments/seismic_event_classification"
    assert s.code_experiment_timeout_seconds == 120
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s4_schemas.py -v`
Expected: FAIL (ModuleNotFoundError / missing fields)

- [ ] **Step 3: Add deps + mounts + settings + schema**

`backend/requirements.txt` — append:
```
numpy>=1.26
scikit-learn>=1.4
```

`backend/Dockerfile` — after `COPY backend/app ./app` add:
```dockerfile
COPY experiments /app/experiments
```

`docker-compose.dev.yml` — under `backend.volumes` add:
```yaml
      - ./experiments:/app/experiments
```

`backend/app/config.py` — add fields to `Settings` (after `data_dir`):
```python
    experiments_dir: Path = Path("experiments/seismic_event_classification")
    code_experiment_timeout_seconds: int = 120
```

`backend/app/schemas/code_experiment.py`:
```python
from typing import Literal

from pydantic import BaseModel, Field


class AcceptanceGate(BaseModel):
    tests_pass: bool = False
    metrics_generated: bool = False
    baseline_comparison_written: bool = False

    @property
    def all_passed(self) -> bool:
        return self.tests_pass and self.metrics_generated and self.baseline_comparison_written


class ComparisonResult(BaseModel):
    baseline_source: str = "harness_trivial"
    baseline_metrics: dict = Field(default_factory=dict)
    method_metrics: dict = Field(default_factory=dict)
    method_beats_baseline: bool = False
    outcome: Literal["completed_positive", "completed_negative", "failed"] = "failed"
    notes: list[str] = Field(default_factory=list)


class FairComparisonPlan(BaseModel):
    method_name: str = "SeismicModel"
    baseline_source: str = "harness_trivial"
    split_strategy: str = "event_level"
    metrics: list[str] = Field(default_factory=lambda: ["accuracy", "macro_f1"])
    preprocessing: str = "raw waveform, event-level split, no leakage"


class IterEntry(BaseModel):
    round: int
    phase: Literal["initial", "repair"] = "initial"
    model_py_hash: str = ""
    tests_passed: bool = False
    traceback_summary: str | None = None


class DebugEntry(BaseModel):
    round: int
    traceback_full: str | None = None
    patch_diff: str | None = None


class ExperimentSummary(BaseModel):
    outcome: Literal["completed_positive", "completed_negative", "failed"] = "failed"
    tests_pass: bool = False
    method_beats_baseline: bool = False
    baseline_source: str = "harness_trivial"
    best_metric: float | None = None
    failure_reason: str | None = None


class CodeExperimentResult(BaseModel):
    harness_version: str = "seismic_sklearn_v1"
    model_family: str = "sklearn"
    baseline_source: str = "harness_trivial"
    model_py_source: str = ""
    fair_comparison_plan: FairComparisonPlan = Field(default_factory=FairComparisonPlan)
    acceptance_gate: AcceptanceGate = Field(default_factory=AcceptanceGate)
    comparison: ComparisonResult = Field(default_factory=ComparisonResult)
    iteration_log: list[IterEntry] = Field(default_factory=list)
    debug_log: list[DebugEntry] = Field(default_factory=list)
    summary: ExperimentSummary = Field(default_factory=ExperimentSummary)
```

`backend/app/schemas/run.py` — add import + field. After `from app.schemas.arena import HypothesisArenaResult`:
```python
from app.schemas.code_experiment import CodeExperimentResult
```
After `experiment_plan: ExperimentPlan | None = None`:
```python
    code_experiment: CodeExperimentResult | None = None
```

- [ ] **Step 4: Rebuild container (new deps + mount) and run test**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build backend`
Then: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s4_schemas.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 2: 合成波形 data.py（harness）

**Files:**
- Create: `experiments/seismic_event_classification/data.py`
- Create: `backend/tests/_s4_harness.py`
- Test: `backend/tests/test_s4_harness_data.py`

**Interfaces:**
- Produces（harness 模块，flat import，sandbox 里 `from data import load_split`）：
  - `LABELS = ("earthquake","explosion","noise")`、`COUNTS`、`SAMPLING_RATE=100`、`WINDOW_SECONDS=30`、`CHANNELS=("Z","N","E")`、`SEED=20260629`。
  - `generate_waveforms() -> tuple[np.ndarray, np.ndarray, np.ndarray]`：返回 `(X(120,3,3000), y(120,), splits(120,))`，确定性。
  - `load_split(split: str) -> tuple[np.ndarray, np.ndarray]`。
  - `save_npz(path)`：写到 `data/seismic_demo/waveforms.npz` 供检查（非闭环必需）。
- Produces（测试 helper）`backend/tests/_s4_harness.py`：`load_harness_module(filename, modname)` 用 importlib 从 walk-up 找到的 harness dir 加载模块（避免 `data` 名字冲撞）。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/_s4_harness.py
import importlib.util
from pathlib import Path


def harness_dir() -> Path:
    p = Path(__file__).resolve()
    for parent in (p.parent, *p.parents):
        cand = parent / "experiments" / "seismic_event_classification"
        if cand.is_dir():
            return cand
    raise RuntimeError("experiments/seismic_event_classification not found (mount ./experiments?)")


def load_harness_module(filename: str, modname: str):
    path = harness_dir() / filename
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
```

```python
# backend/tests/test_s4_harness_data.py
import numpy as np

from _s4_harness import load_harness_module


def test_waveforms_deterministic_and_shaped() -> None:
    data = load_harness_module("data.py", "s4_data")
    X1, y1, s1 = data.generate_waveforms()
    X2, y2, s2 = data.generate_waveforms()
    assert X1.shape == (120, 3, 3000)
    assert len(y1) == 120 and len(s1) == 120
    np.testing.assert_array_equal(X1, X2)
    assert set(np.unique(y1)) == set(data.LABELS)
    assert set(np.unique(s1)) == {"train", "val", "test"}


def test_load_split_consistency() -> None:
    data = load_harness_module("data.py", "s4_data")
    Xtr, ytr = data.load_split("train")
    Xte, yte = data.load_split("test")
    assert Xtr.shape[1:] == (3, 3000)
    assert len(Xtr) + len(data.load_split("val")[0]) + len(Xte) == 120
    assert set(ytr).issubset(set(data.LABELS))


def test_waveforms_separable_by_frequency_not_time_stats() -> None:
    """Sanity: a frequency-feature classifier beats a time-domain-stats baseline.
    Proves the synthetic data carries real separable signal (not rigged, but learnable)."""
    from sklearn.linear_model import LogisticRegression

    data = load_harness_module("data.py", "s4_data")
    X, y, splits = data.generate_waveforms()
    Xtr, ytr = X[splits == "train"], y[splits == "train"]
    Xte, yte = X[splits == "test"], y[splits == "test"]

    def time_feats(X):
        return np.concatenate(
            [X.mean(2), X.std(2), np.abs(X).max(2), (X ** 2).mean(2)], axis=1)

    def freq_feats(X):
        n = X.shape[2]
        spec = np.abs(np.fft.rfft(X, axis=2))
        freqs = np.fft.rfftfreq(n, d=1.0 / data.SAMPLING_RATE)
        peak = freqs[spec.argmax(2)]  # (N, C)
        bands = [(0, 3), (3, 10), (10, 30)]
        band_e = [spec[:, :, (freqs >= lo) & (freqs < hi)].sum(2) for lo, hi in bands]
        return np.concatenate([peak] + band_e, axis=1)

    baseline = LogisticRegression(max_iter=2000, class_weight="balanced").fit(time_feats(Xtr), ytr)
    method = LogisticRegression(max_iter=2000, class_weight="balanced").fit(freq_feats(Xtr), ytr)
    b_acc = (baseline.predict(time_feats(Xte)) == yte).mean()
    m_acc = (method.predict(freq_feats(Xte)) == yte).mean()
    assert m_acc > b_acc, f"freq feats must beat time stats: {m_acc} vs {b_acc}"
    assert m_acc > 0.8, f"data must be learnable: {m_acc}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s4_harness_data.py -v`
Expected: FAIL (FileNotFoundError / no data.py)

- [ ] **Step 3: Write data.py**

```python
# experiments/seismic_event_classification/data.py
"""Deterministic synthetic seismic waveforms for the S4 Code Experiment Loop.

120 events x 3 channels (Z/N/E) x 30s @ 100Hz = 3000 samples. Three classes
designed so time-domain statistics (mean/std/peak/energy) are UNINFORMATIVE
but spectral content separates them: earthquake = low-freq sine (1-3 Hz),
explosion = high-freq sine (10-20 Hz), noise = broadband white — each
normalized to unit RMS so std/energy match across classes (sines share the
same peak too; only noise has a higher Gaussian peak). A frequency-feature
model therefore genuinely beats a time-domain-statistics baseline; a dumb
model that only uses time stats ties the baseline (completed_negative).
Per-channel rotation/attenuation makes multi-channel features useful.

Pure numpy (no scipy). Seed fixed -> reproducible. Real STEAD subset lands in S7.
"""
import pathlib

import numpy as np

LABELS = ("earthquake", "explosion", "noise")
COUNTS = {"earthquake": 60, "explosion": 35, "noise": 25}
SAMPLING_RATE = 100
WINDOW_SECONDS = 30
CHANNELS = ("Z", "N", "E")
SEED = 20260629
_N = WINDOW_SECONDS * SAMPLING_RATE  # 3000


def _unit_rms(sig: np.ndarray) -> np.ndarray:
    return sig / (np.sqrt(np.mean(sig ** 2)) + 1e-8)


def _gen_event(label: str, n: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SAMPLING_RATE
    if label == "earthquake":
        f = rng.uniform(1.0, 3.0)
        sig = np.sin(2 * np.pi * f * t)
    elif label == "explosion":
        f = rng.uniform(10.0, 20.0)
        sig = np.sin(2 * np.pi * f * t)
    else:  # noise
        sig = rng.standard_normal(n)
    # Unit RMS so mean/std/energy are class-invariant and sines share the same
    # peak — only spectral content (and noise's higher Gaussian peak) separates
    # classes. This is what makes a frequency-feature model beat a time-stats
    # baseline without rigging the data.
    return _unit_rms(sig)


def generate_waveforms():
    """Return (X(120,3,3000), y(120,), splits(120,)) deterministically."""
    rng = np.random.default_rng(SEED)
    nchan = len(CHANNELS)
    X, y, splits = [], [], []
    eid = 0
    for label, count in COUNTS.items():
        for _ in range(count):
            eid += 1
            base = _gen_event(label, _N, rng)
            wave = np.zeros((nchan, _N))
            for c in range(nchan):
                amp = 1.0 - 0.05 * c
                # Scalar per-channel attenuation only — NO time-shift rotation,
                # because np.roll(base, 1) is a frequency-dependent phase shift
                # (high-freq sines degrade faster across channels) that leaks
                # spectral info into per-channel std and lets a time-stats
                # baseline separate eq from explosion. Scalar amp keeps std
                # class-invariant; only peak (noise's higher Gaussian max vs
                # sines' sqrt(2)) leaks, capping the baseline well below the
                # freq-feature model.
                wave[c] = amp * base + 0.05 * rng.standard_normal(_N)
            X.append(wave)
            y.append(label)
            # 60% train / 20% val / 20% test, deterministic per event id.
            splits.append(["train", "train", "train", "val", "test"][eid % 5])
    return np.stack(X), np.array(y), np.array(splits)


def load_split(split: str):
    X, y, splits = generate_waveforms()
    mask = splits == split
    return X[mask], y[mask]


def save_npz(path) -> None:
    X, y, splits = generate_waveforms()
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez(p, X=X, y=y, splits=splits, channels=np.array(CHANNELS))


if __name__ == "__main__":
    save_npz(pathlib.Path("data/seismic_demo/waveforms.npz"))
    print("wrote data/seismic_demo/waveforms.npz")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s4_harness_data.py -v`
Expected: PASS (3 tests). If separability test is flaky, the seed is fixed so it must be stable.

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 3: harness baseline.py + tests.py + train.py + manifest

**Files:**
- Create: `experiments/seismic_event_classification/baseline.py`
- Create: `experiments/seismic_event_classification/tests.py`
- Create: `experiments/seismic_event_classification/train.py`
- Create: `experiments/seismic_event_classification/harness_manifest.json`
- Create: `experiments/seismic_event_classification/model_template.py`（参考骨架，非闭环依赖）
- Test: `backend/tests/test_s4_harness.py`

**Interfaces:**
- `baseline.BaselineModel`：`fit(X,y)`/`predict(X)`，时域统计 + LogisticRegression。
- `model.SeismicModel`（LLM 写）：`fit(X,y)`/`predict(X)`。`tests.py` 检这个接口。
- `tests.py`：exit 0 = 接口/shape/NaN/label 全过；exit 1 = 写 `tests_failed.flag` + 打印错误。
- `train.py`：跑完写 `metrics.json`、`comparison.json`（固定 schema）。
- `tests.py` 是 acceptance_gate 的 `tests_pass` 来源；`metrics_generated`/`baseline_comparison_written` 由 workflow 在 train 后查文件存在性设置（**不在 tests.py 里查**，因为 tests.py 在 train 之前跑）。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_s4_harness.py
import json
import subprocess
import textwrap
from pathlib import Path

from _s4_harness import harness_dir, load_harness_module


def _write_model(sandbox: Path, source: str) -> None:
    (sandbox / "model.py").write_text(source, encoding="utf-8")


def _copy_harness(sandbox: Path) -> None:
    import shutil
    for fn in ("data.py", "baseline.py", "train.py", "tests.py", "harness_manifest.json"):
        shutil.copy(harness_dir() / fn, sandbox / fn)


def _run(script: str, sandbox: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["python", script], cwd=sandbox, capture_output=True, text=True, timeout=120)


GOOD_MODEL = textwrap.dedent('''
    import numpy as np
    from sklearn.linear_model import LogisticRegression

    class SeismicModel:
        def __init__(self):
            self.clf = LogisticRegression(max_iter=2000, class_weight="balanced")
        def _f(self, X):
            return np.concatenate([X.mean(2), X.std(2), np.abs(X).max(2), (X**2).mean(2)], axis=1)
        def fit(self, X, y):
            self.clf.fit(self._f(X), y); return self
        def predict(self, X):
            return self.clf.predict(self._f(X))
''')

BAD_SHAPE_MODEL = textwrap.dedent('''
    import numpy as np
    class SeismicModel:
        def fit(self, X, y): return self
        def predict(self, X):
            # wrong length on purpose
            return np.array(["earthquake"] * (len(X) - 1))
''')

NAN_MODEL = textwrap.dedent('''
    import numpy as np
    class SeismicModel:
        def fit(self, X, y): return self
        def predict(self, X):
            out = np.array(["earthquake"] * len(X), dtype=object)
            out[0] = np.nan
            return out
''')

BAD_LABEL_MODEL = textwrap.dedent('''
    import numpy as np
    class SeismicModel:
        def fit(self, X, y): return self
        def predict(self, X):
            return np.array(["covid"] * len(X))
''')


def test_tests_py_passes_good_model(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, GOOD_MODEL)
    r = _run("tests.py", sb)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "TESTS PASSED" in r.stdout


def test_tests_py_catches_shape_mismatch(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, BAD_SHAPE_MODEL)
    r = _run("tests.py", sb)
    assert r.returncode == 1
    assert (sb / "tests_failed.flag").exists()


def test_tests_py_catches_nan_predictions(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, NAN_MODEL)
    r = _run("tests.py", sb)
    assert r.returncode == 1


def test_tests_py_catches_invalid_labels(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, BAD_LABEL_MODEL)
    r = _run("tests.py", sb)
    assert r.returncode == 1


def test_train_py_writes_artifacts_and_comparison_schema(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, GOOD_MODEL)
    r = _run("train.py", sb)
    assert r.returncode == 0, r.stdout + r.stderr
    comp = json.loads((sb / "comparison.json").read_text())
    assert set(comp) == {"baseline_source", "baseline_metrics", "method_metrics",
                         "method_beats_baseline", "outcome", "notes"}
    assert comp["baseline_source"] == "harness_trivial"
    assert comp["outcome"] in {"completed_positive", "completed_negative"}
    assert "accuracy" in comp["method_metrics"]
    metrics = json.loads((sb / "metrics.json").read_text())
    assert "baseline" in metrics and "method" in metrics


def test_manifest_shape():
    m = json.loads((harness_dir() / "harness_manifest.json").read_text())
    assert m["model_family"] == "sklearn"
    assert m["harness_version"] == "seismic_sklearn_v1"
    assert m["max_repair_rounds"] == 3
    assert m["baseline_source"] == "harness_trivial"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s4_harness.py -v`
Expected: FAIL (harness files missing)

- [ ] **Step 3: Write harness files**

`experiments/seismic_event_classification/baseline.py`:
```python
"""Fixed weak baseline: per-channel time-domain stats + LogisticRegression.
LLM never edits this. It is the fair-comparison anchor (baseline_source=harness_trivial)."""
import numpy as np
from sklearn.linear_model import LogisticRegression


class BaselineModel:
    def __init__(self):
        self.clf = LogisticRegression(max_iter=2000, class_weight="balanced")

    def _features(self, X):
        return np.concatenate(
            [X.mean(2), X.std(2), np.abs(X).max(2), (X ** 2).mean(2)], axis=1)

    def fit(self, X, y):
        self.clf.fit(self._features(X), y)
        return self

    def predict(self, X):
        return self.clf.predict(self._features(X))
```

`experiments/seismic_event_classification/tests.py`:
```python
"""Acceptance-gate pre-check (runs BEFORE train.py). Verifies the LLM-written
model.py is importable, has the fit/predict interface, and produces predictions
with correct length, valid labels, and no NaN/inf. metrics.json/comparison.json
existence is checked by the workflow AFTER train (not here)."""
import math
import pathlib
import sys
import traceback

import numpy as np

from data import LABELS, load_split


def _has_nan_or_inf(arr) -> bool:
    """Dtype-agnostic NaN/inf check: predictions may be string labels (object
    dtype) with a stray float NaN, which np.isfinite would refuse on object
    arrays. Walk values explicitly."""
    for v in np.asarray(arr).ravel():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return True
    return False


def _run():
    errors = []
    try:
        from model import SeismicModel
        m = SeismicModel()
        if not (hasattr(m, "fit") and hasattr(m, "predict")):
            errors.append("SeismicModel missing fit/predict")
            return errors
    except Exception as e:  # noqa: BLE001
        errors.append(f"model import/interface failed: {e!r}")
        return errors
    try:
        Xtr, ytr = load_split("train")
        Xte, yte = load_split("test")
        m.fit(Xtr, ytr)
        pred = np.asarray(m.predict(Xte))
        if len(pred) != len(yte):
            errors.append(f"len(pred)={len(pred)} != len(y_test)={len(yte)}")
        if not set(np.unique(pred)).issubset(set(LABELS)):
            errors.append(f"pred labels {set(np.unique(pred))} not subset of {set(LABELS)}")
        if _has_nan_or_inf(pred):
            errors.append("predictions contain NaN/inf")
    except Exception:  # noqa: BLE001
        errors.append("fit/predict raised:\n" + traceback.format_exc())
    return errors


def main() -> int:
    errors = _run()
    if errors:
        print("TESTS FAILED:")
        for e in errors:
            print(e)
        pathlib.Path("tests_failed.flag").write_text("failed", encoding="utf-8")
        return 1
    print("TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`experiments/seismic_event_classification/train.py`:
```python
"""Fixed harness: train baseline + method on train split, eval on test split,
write metrics.json + comparison.json (fixed schema)."""
import json
import pathlib

import numpy as np

from baseline import BaselineModel
from data import load_split
from model import SeismicModel

METRICS_PATH = pathlib.Path("metrics.json")
COMPARISON_PATH = pathlib.Path("comparison.json")


def _metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    acc = float((y_pred == y_true).mean())
    f1s = {}
    for label in sorted(set(y_true) | set(y_pred)):
        tp = int(((y_pred == label) & (y_true == label)).sum())
        fp = int(((y_pred == label) & (y_true != label)).sum())
        fn = int(((y_pred != label) & (y_true == label)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s[label] = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    macro_f1 = float(np.mean(list(f1s.values()))) if f1s else 0.0
    return {"accuracy": acc, "macro_f1": macro_f1, "per_class_f1": f1s}


def main() -> int:
    Xtr, ytr = load_split("train")
    Xte, yte = load_split("test")
    baseline = BaselineModel().fit(Xtr, ytr)
    method = SeismicModel().fit(Xtr, ytr)
    b = _metrics(yte, baseline.predict(Xte))
    m = _metrics(yte, method.predict(Xte))
    METRICS_PATH.write_text(json.dumps({"baseline": b, "method": m}, indent=2), encoding="utf-8")
    beats = m["accuracy"] > b["accuracy"]
    outcome = "completed_positive" if beats else "completed_negative"
    COMPARISON_PATH.write_text(json.dumps({
        "baseline_source": "harness_trivial",
        "baseline_metrics": b,
        "method_metrics": m,
        "method_beats_baseline": bool(beats),
        "outcome": outcome,
        "notes": [],
    }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`experiments/seismic_event_classification/harness_manifest.json`:
```json
{
  "model_family": "sklearn",
  "harness_version": "seismic_sklearn_v1",
  "max_repair_rounds": 3,
  "baseline_source": "harness_trivial",
  "acceptance_gate": ["tests_pass", "metrics_generated", "baseline_comparison_written"]
}
```

`experiments/seismic_event_classification/model_template.py`（参考骨架，文档/调试用，闭环不依赖）:
```python
"""Reference skeleton SeismicModel. The CodeWriterAgent fallback emits a model
like this. LLM-written model.py replaces it at runtime in the sandbox."""
import numpy as np
from sklearn.linear_model import LogisticRegression


class SeismicModel:
    def __init__(self):
        self.clf = LogisticRegression(max_iter=2000, class_weight="balanced")

    def _features(self, X):
        return np.concatenate(
            [X.mean(2), X.std(2), np.abs(X).max(2), (X ** 2).mean(2)], axis=1)

    def fit(self, X, y):
        self.clf.fit(self._features(X), y)
        return self

    def predict(self, X):
        return self.clf.predict(self._features(X))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s4_harness.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 4: SandboxExecutor

**Files:**
- Create: `backend/app/tools/sandbox_executor.py`
- Test: `backend/tests/test_sandbox_executor.py`

**Interfaces:**
- `SandboxExecutor(harness_dir: Path, timeout: int = 120)`
- `SandboxExecutor.ALLOWED = ("tests.py", "train.py")`
- `.prepare(sandbox_dir: Path, model_py_source: str) -> None`：拷 harness 5 文件 + 写 `model.py`。
- `.run(sandbox_dir: Path, script: str) -> SandboxRunResult`：白名单外 raise `ValueError`；subprocess capture stdout/stderr/exit code + timeout。
- `SandboxRunResult(exit_code: int, stdout: str, stderr: str, timed_out: bool)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_sandbox_executor.py
import time

from app.tools.sandbox_executor import SandboxExecutor, SandboxRunResult


def test_prepare_copies_harness_and_writes_model(tmp_path):
    sb = tmp_path / "sb"
    ex = SandboxExecutor(harness_dir="experiments/seismic_event_classification", timeout=10)
    ex.prepare(sb, "class SeismicModel:\n    pass\n")
    for fn in ("data.py", "baseline.py", "train.py", "tests.py", "harness_manifest.json", "model.py"):
        assert (sb / fn).exists(), fn
    assert (sb / "model.py").read_text().startswith("class SeismicModel")


def test_run_rejects_non_whitelisted_script(tmp_path):
    ex = SandboxExecutor(harness_dir="experiments/seismic_event_classification", timeout=5)
    ex.prepare(tmp_path / "sb", "class SeismicModel:\n    pass\n")
    try:
        ex.run(tmp_path / "sb", "evil.py")
        assert False, "should have raised"
    except ValueError:
        pass


def test_run_captures_exit_code_and_stdout(tmp_path):
    # Use a tmp harness dir whose tests.py just prints + exits 0
    import shutil, pathlib
    hd = tmp_path / "harness"; hd.mkdir()
    (hd / "data.py").write_text("LABELS=()\ndef load_split(s):\n    import numpy as np; return np.zeros((1,3,10)), np.array([])\n")
    (hd / "baseline.py").write_text("class BaselineModel:\n    pass\n")
    (hd / "train.py").write_text("print('hello from train')\n")
    (hd / "tests.py").write_text("print('hi from tests')\n")
    (hd / "harness_manifest.json").write_text("{}\n")
    ex = SandboxExecutor(harness_dir=hd, timeout=10)
    sb = tmp_path / "sb"
    ex.prepare(sb, "class SeismicModel:\n    pass\n")
    r = ex.run(sb, "tests.py")
    assert isinstance(r, SandboxRunResult)
    assert r.exit_code == 0
    assert "hi from tests" in r.stdout
    assert not r.timed_out
    r2 = ex.run(sb, "train.py")
    assert "hello from train" in r2.stdout


def test_run_reports_timeout(tmp_path):
    import pathlib
    hd = tmp_path / "harness"; hd.mkdir()
    (hd / "data.py").write_text("LABELS=()\n")
    (hd / "baseline.py").write_text("class BaselineModel: pass\n")
    (hd / "train.py").write_text("import time; time.sleep(5)\n")
    (hd / "tests.py").write_text("import time; time.sleep(5)\n")
    (hd / "harness_manifest.json").write_text("{}\n")
    ex = SandboxExecutor(harness_dir=hd, timeout=1)
    sb = tmp_path / "sb"
    ex.prepare(sb, "class SeismicModel:\n    pass\n")
    r = ex.run(sb, "tests.py")
    assert r.timed_out is True
    assert r.exit_code == -1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_sandbox_executor.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write SandboxExecutor**

```python
# backend/app/tools/sandbox_executor.py
"""Controlled subprocess sandbox for the S4 Code Experiment Loop.

Copies the fixed harness (data/baseline/train/tests/manifest) + the LLM-written
model.py into an isolated per-run directory and runs only whitelisted scripts
(`python tests.py` / `python train.py`) with a timeout. Same backend container
(no sidecar); network isolation is policy-level (no pip, deps pre-installed) —
true OS-level isolation is deferred to S7 hardening."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_HARNESS_FILES = ("data.py", "baseline.py", "train.py", "tests.py", "harness_manifest.json")


@dataclass
class SandboxRunResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


class SandboxExecutor:
    ALLOWED = ("tests.py", "train.py")

    def __init__(self, harness_dir: Path, timeout: int = 120) -> None:
        self.harness_dir = Path(harness_dir)
        self.timeout = timeout

    def prepare(self, sandbox_dir: Path, model_py_source: str) -> None:
        sandbox_dir = Path(sandbox_dir)
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        for fn in _HARNESS_FILES:
            src = self.harness_dir / fn
            if src.exists():
                shutil.copy(src, sandbox_dir / fn)
        (sandbox_dir / "model.py").write_text(model_py_source, encoding="utf-8")

    def run(self, sandbox_dir: Path, script: str) -> SandboxRunResult:
        if script not in self.ALLOWED:
            raise ValueError(f"disallowed script: {script!r} (whitelist={self.ALLOWED})")
        sandbox_dir = Path(sandbox_dir)
        try:
            proc = subprocess.run(
                ["python", script],
                cwd=str(sandbox_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return SandboxRunResult(proc.returncode, proc.stdout, proc.stderr, False)
        except subprocess.TimeoutExpired as e:
            return SandboxRunResult(
                -1, e.stdout or "", e.stderr or "", True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_sandbox_executor.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 5: CodeWriterAgent（LCEL，骨架 fallback）

**Files:**
- Create: `backend/app/agents/code_writer_agent.py`
- Test: `backend/tests/test_code_writer_agent.py`

**Interfaces:**
- `CodeWriterAgent(llm: LLMClient | None = None)`
- `async arun(mode: Literal["initial","repair"], hypothesis, experiment_plan, *, current_source=None, traceback=None, run_id) -> str`：返回 `model.py` 源码字符串。
- `FALLBACK_MODEL_PY`：骨架 `SeismicModel`（统计特征 + LogisticRegression），保证接口合规、跑得起来但弱。
- LLM 输出非 JSON（是 Python 源码），用自定义 `_CodeExtractor(Runnable)` 提取 ```python 块或裸代码，无 `class SeismicModel` 则落 fallback。

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_code_writer_agent.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write CodeWriterAgent**

```python
# backend/app/agents/code_writer_agent.py
"""CodeWriterAgent — LCEL agent that writes/repairs the harness model.py.

Two prompt modes: 'initial' (from Top1 hypothesis + experiment plan + harness
interface spec) and 'repair' (from current source + last traceback). LLM output
is Python source (not JSON), so a custom _CodeExtractor pulls the code block
and falls back to a skeleton SeismicModel on any failure — guaranteeing the
harness can always produce a comparison (even if completed_negative)."""
from __future__ import annotations

import re
from typing import Literal

from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient, LLMResponseFormat
from app.llm.langchain_adapter import LLMClientRunnable, build_agent_prompt
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis

FALLBACK_MODEL_PY = '''"""Skeleton SeismicModel emitted when the LLM output is unusable.
Not meant to win — meant to keep the harness running so a comparison is produced."""
import numpy as np
from sklearn.linear_model import LogisticRegression


class SeismicModel:
    def __init__(self):
        self.clf = LogisticRegression(max_iter=2000, class_weight="balanced")

    def _features(self, X):
        return np.concatenate(
            [X.mean(2), X.std(2), np.abs(X).max(2), (X ** 2).mean(2)], axis=1)

    def fit(self, X, y):
        self.clf.fit(self._features(X), y)
        return self

    def predict(self, X):
        return self.clf.predict(self._features(X))
'''

SYSTEM_PROMPT = """You are the Code Writer for TrustSci-Agent v3 seismic Code Experiment Loop.
You write ONLY the file `model.py` — a single Python class `SeismicModel` with:
  def fit(self, X, y) -> self
  def predict(self, X) -> array-like of labels
X is a numpy array of shape (N, 3, 3000): N events, 3 channels (Z/N/E), 3000 samples @ 100Hz.
Labels are one of: earthquake, explosion, noise.
Available libs: numpy, scikit-learn (sklearn). Do NOT import torch/scipy/anything not installed.
Do NOT read files, do NOT use network. fit/predict must be self-contained.
Return ONLY a single ```python code block``` containing model.py — no prose.
The class MUST be named `SeismicModel` and implement both fit() and predict().
"""

INITIAL_TEMPLATE = """Hypothesis (Top1 from Arena):
{hypothesis}

Experiment plan:
{plan}

Write model.py implementing the hypothesis as SeismicModel. Beat the baseline
(per-channel time-domain statistics + LogisticRegression) using the hypothesis's
approach (e.g. spectral / multi-channel features)."""

REPAIR_TEMPLATE = """The previous model.py failed. Current source:
```python
{current_source}
```

Traceback / failure:
```
{traceback}
```

Rewrite model.py (full file, single ```python block```) fixing the failure. Keep
the SeismicModel class with fit()/predict()."""


class _CodeExtractor(Runnable):
    def __init__(self, fallback: str) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> str:
        if not isinstance(content, str):
            return self.fallback
        m = re.search(r"```(?:python)?\s*(.*?)```", content, re.S)
        text = m.group(1) if m else content
        text = text.strip()
        if "class SeismicModel" not in text:
            return self.fallback
        if "def fit" not in text or "def predict" not in text:
            return self.fallback
        return text

    def invoke(self, input, config=None, **kwargs):
        return self.parse(input)

    async def ainvoke(self, input, config=None, **kwargs):
        return self.parse(input)


class CodeWriterAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm
        self._prompt = build_agent_prompt(SYSTEM_PROMPT)

    async def arun(
        self,
        mode: Literal["initial", "repair"],
        hypothesis: Hypothesis | None,
        experiment_plan: ExperimentPlan | None,
        *,
        current_source: str | None = None,
        traceback: str | None = None,
        run_id: str,
    ) -> str:
        if mode == "repair":
            user_prompt = REPAIR_TEMPLATE.format(
                current_source=current_source or "",
                traceback=traceback or "(no traceback)",
            )
        else:
            user_prompt = INITIAL_TEMPLATE.format(
                hypothesis=_fmt_hypothesis(hypothesis),
                plan=_fmt_plan(experiment_plan),
            )
        if self.llm is None:
            return FALLBACK_MODEL_PY
        chain = (
            self._prompt
            | LLMClientRunnable(self.llm, response_format=LLMResponseFormat.text).bind(
                fallback=FALLBACK_MODEL_PY, run_id=run_id, agent="code_writer")
            | _CodeExtractor(FALLBACK_MODEL_PY)
        )
        return await chain.ainvoke({"user_prompt": user_prompt})


def _fmt_hypothesis(h: Hypothesis | None) -> str:
    if h is None:
        return "(none)"
    return f"statement: {h.statement}\nrationale: {h.rationale}\nverification_path: {h.verification_path}"


def _fmt_plan(p: ExperimentPlan | None) -> str:
    if p is None:
        return "(none)"
    return (f"datasets: {p.datasets}\nbaselines: {p.baselines}\n"
            f"metrics: {p.metrics}\nsteps: {p.experiment_steps}\n"
            f"expected: {p.expected_results}")
```

> Note（已核对 `langchain_adapter.py` / `interface.py` / `qwen_client.py`）：
> - `build_agent_prompt` 返回 `ChatPromptTemplate`，单一 `{user_prompt}` 槽，`chain.ainvoke({"user_prompt": ...})` 正确。
> - **必须 `response_format=LLMResponseFormat.text`**：默认 `json` 会让 Qwen API 强制 `{"type":"json_object"}` 输出（模型会把代码包进 JSON），且 `QwenClient.complete` 在 json 模式下返回 dict、在 text 模式下返回 str。`_CodeExtractor` 只接受 str，故必须 text 模式。
> - text 模式下 LLM 调用抛错时 `QwenClient.chat_text` 返回 `str(request.fallback)` = `FALLBACK_MODEL_PY`，`_CodeExtractor` 再放行 → 闭环永不卡死。
> - `LLMRequest` 字段是 `user`（非 `user_prompt`）；审计日志列名才是 `user_prompt`。

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_code_writer_agent.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 6: FairComparisonPlanner（确定性，无 LLM）

**Files:**
- Create: `backend/app/agents/fair_comparison_planner.py`
- Test: `backend/tests/test_fair_comparison_planner.py`

**Interfaces:**
- `FairComparisonPlanner.plan(*, baseline_source="harness_trivial") -> FairComparisonPlan`：固定同 split/同 metric/同预处理。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_fair_comparison_planner.py
from app.agents.fair_comparison_planner import FairComparisonPlanner
from app.schemas.code_experiment import FairComparisonPlan


def test_plan_shape_and_defaults() -> None:
    p = FairComparisonPlanner().plan()
    assert isinstance(p, FairComparisonPlan)
    assert p.method_name == "SeismicModel"
    assert p.baseline_source == "harness_trivial"
    assert p.split_strategy == "event_level"
    assert "accuracy" in p.metrics and "macro_f1" in p.metrics
    assert "no leakage" in p.preprocessing


def test_plan_respects_baseline_source() -> None:
    p = FairComparisonPlanner().plan(baseline_source="verified_repo")
    assert p.baseline_source == "verified_repo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_fair_comparison_planner.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write FairComparisonPlanner**

```python
# backend/app/agents/fair_comparison_planner.py
"""Deterministic fair-comparison planner (no LLM).

Fairness is mechanical, not a judgment call: same event-level split, same
metrics, same preprocessing for method and baseline. Only the method (model.py)
varies. This object is surfaced to the report + CodePlanPanel so the fairness
contract is explicit rather than implicit."""
from app.schemas.code_experiment import FairComparisonPlan


class FairComparisonPlanner:
    def plan(self, *, baseline_source: str = "harness_trivial") -> FairComparisonPlan:
        return FairComparisonPlan(
            method_name="SeismicModel",
            baseline_source=baseline_source,
            split_strategy="event_level",
            metrics=["accuracy", "macro_f1"],
            preprocessing="raw waveform, fixed event-level train/val/test split, "
                          "same preprocessing for method and baseline, no leakage",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_fair_comparison_planner.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 7: micro 闭环 `_run_code_experiment`

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py`（`__init__` 装依赖 + 加 `_run_code_experiment` step + `_run_after_evidence_review` 插入）
- Test: `backend/tests/test_code_experiment_loop.py`

**Interfaces:**
- Consumes: `CodeWriterAgent`、`SandboxExecutor`、`FairComparisonPlanner`、`Settings.experiments_dir`、`Settings.code_experiment_timeout_seconds`、`_selected_hypothesis(run.hypotheses)`、`run.experiment_plan`。
- Produces: `ResearchRun.code_experiment: CodeExperimentResult`。
- 闭环伪码：
  ```
  source = CodeWriter(initial)
  for rnd in 1..max_repair_rounds:
      sandbox.prepare(sandbox_dir, source)
      res = sandbox.run(tests.py)
      tests_pass = (res.exit_code==0)
      log round
      if tests_pass: break
      if rnd < max: source = CodeWriter(repair, current=source, traceback=res.stderr)
  if not tests_pass: outcome=failed; skip train
  else:
      sandbox.run(train.py)
      gate.metrics_generated = metrics.json exists
      gate.baseline_comparison_written = comparison.json exists
      if both: comparison = ComparisonResult(**comparison.json); outcome from file
      else: outcome=failed (train 崩)
  summary = ExperimentSummary(...)
  ```

- [ ] **Step 1: Write the failing test (4 scenarios via fakes)**

```python
# backend/tests/test_code_experiment_loop.py
import json

import pytest

from app.config import Settings
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


GOOD_SRC = "class SeismicModel:\n    def fit(self,X,y): return self\n    def predict(self,X): return ['earthquake']*len(X)\n"


class FakeCodeWriter:
    def __init__(self, sources):
        self.sources = list(sources)
        self.calls = []
    async def arun(self, mode, hypothesis, plan, *, current_source=None, traceback=None, run_id):
        self.calls.append((mode, traceback))
        return self.sources.pop(0) if self.sources else GOOD_SRC


class _R:
    def __init__(self, exit_code, stderr=""):
        self.exit_code = exit_code
        self.stdout = ""
        self.stderr = stderr
        self.timed_out = False


class FakeSandbox:
    """Parametrizable fake: tests_results is a list of (exit_code, stderr)
    consumed one per tests.py call. train.py writes metrics+comparison from
    method_acc/baseline_acc unless train_crash=True."""
    def __init__(self, *, tests_results, method_acc=0.9, baseline_acc=0.5,
                 train_crash=False, write_artifacts=True):
        self.tests_results = list(tests_results)
        self.method_acc = method_acc
        self.baseline_acc = baseline_acc
        self.train_crash = train_crash
        self.write_artifacts = write_artifacts
        self.scripts_run: list[str] = []
    def prepare(self, sandbox_dir, model_py_source):
        import pathlib
        pathlib.Path(sandbox_dir).mkdir(parents=True, exist_ok=True)
    def run(self, sandbox_dir, script):
        import json, pathlib
        self.scripts_run.append(script)
        if script == "tests.py":
            ec, stderr = self.tests_results.pop(0)
            return _R(ec, stderr)
        if script == "train.py":
            if self.train_crash:
                return _R(1, "train boom")
            if self.write_artifacts:
                pathlib.Path(sandbox_dir, "metrics.json").write_text(json.dumps(
                    {"baseline": {"accuracy": self.baseline_acc},
                     "method": {"accuracy": self.method_acc}}))
                beats = self.method_acc > self.baseline_acc
                pathlib.Path(sandbox_dir, "comparison.json").write_text(json.dumps({
                    "baseline_source": "harness_trivial",
                    "baseline_metrics": {"accuracy": self.baseline_acc},
                    "method_metrics": {"accuracy": self.method_acc},
                    "method_beats_baseline": bool(beats),
                    "outcome": "completed_positive" if beats else "completed_negative",
                    "notes": []}))
            return _R(0)
        raise ValueError(f"unexpected script {script}")


def _wf_with(code_writer, sandbox):
    wf = ScientistWorkflow(Settings(dashscope_api_key="", max_papers=2))
    wf.code_writer = code_writer
    wf.sandbox_executor = sandbox
    return wf


def _run():
    r = ResearchRun(domain="seismic_event_classification", question="q",
                    constraints=ResearchConstraints(), mode="discovery")
    r.hypotheses = [Hypothesis(hypothesis_id="H1", statement="s", rationale="r",
                               novelty_claim="n", verification_path="v", selected=True)]
    r.experiment_plan = ExperimentPlan(datasets=["d"], source="s", target="t",
                                       baselines=["b"], metrics=["accuracy"],
                                       experiment_steps=["x"], expected_results="e")
    return r


@pytest.mark.asyncio
async def test_scenario_tests_pass_completed_positive(tmp_path, monkeypatch):
    wf = _wf_with(FakeCodeWriter([GOOD_SRC]),
                  FakeSandbox(tests_results=[(0, "")], method_acc=0.9, baseline_acc=0.5))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce is not None
    assert ce.acceptance_gate.tests_pass is True
    assert ce.acceptance_gate.metrics_generated is True
    assert ce.acceptance_gate.baseline_comparison_written is True
    assert ce.comparison.outcome == "completed_positive"
    assert ce.summary.outcome == "completed_positive"
    assert ce.summary.method_beats_baseline is True
    assert ce.summary.best_metric == 0.9
    assert len(ce.iteration_log) == 1
    assert ce.iteration_log[0].phase == "initial"


@pytest.mark.asyncio
async def test_scenario_tests_fail_three_rounds_then_failed_skip_train(tmp_path, monkeypatch):
    wf = _wf_with(FakeCodeWriter([GOOD_SRC, GOOD_SRC, GOOD_SRC]),
                  FakeSandbox(tests_results=[(1, "err1"), (1, "err2"), (1, "err3")]))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce.acceptance_gate.tests_pass is False
    assert ce.acceptance_gate.metrics_generated is False
    assert ce.acceptance_gate.baseline_comparison_written is False
    assert ce.comparison.outcome == "failed"
    assert ce.summary.outcome == "failed"
    assert ce.summary.failure_reason
    assert len(ce.iteration_log) == 3
    # train.py must NEVER have been called (tests never passed)
    assert "train.py" not in wf.sandbox_executor.scripts_run
    # repair was attempted between rounds (2 repair calls for 3 rounds)
    assert [c[0] for c in wf.code_writer.calls] == ["initial", "repair", "repair"]


@pytest.mark.asyncio
async def test_scenario_fallback_skeleton_then_completed_negative(tmp_path, monkeypatch):
    # CodeWriter returns the (interface-valid) fallback skeleton; tests pass;
    # train produces a comparison where method does NOT beat baseline.
    wf = _wf_with(FakeCodeWriter(["# fallback emitted"]),
                  FakeSandbox(tests_results=[(0, "")], method_acc=0.4, baseline_acc=0.8))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce.acceptance_gate.tests_pass is True
    assert ce.comparison.outcome == "completed_negative"
    assert ce.summary.outcome == "completed_negative"
    assert ce.summary.method_beats_baseline is False
    assert ce.summary.best_metric == 0.4


@pytest.mark.asyncio
async def test_scenario_train_crash_then_failed(tmp_path, monkeypatch):
    # tests pass round 1, but train.py crashes (no artifacts) -> failed
    wf = _wf_with(FakeCodeWriter([GOOD_SRC]),
                  FakeSandbox(tests_results=[(0, "")], train_crash=True, write_artifacts=False))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce.acceptance_gate.tests_pass is True
    assert ce.acceptance_gate.metrics_generated is False
    assert ce.acceptance_gate.baseline_comparison_written is False
    assert ce.comparison.outcome == "failed"
    assert ce.summary.outcome == "failed"
    assert ce.summary.failure_reason
    assert ce.summary.best_metric is None


@pytest.mark.asyncio
async def test_non_seismic_skips_code_experiment():
    wf = _wf_with(FakeCodeWriter([]), FakeSandbox(tests_results=[]))
    r = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    await wf._run_code_experiment(r)
    assert r.code_experiment is None  # non-seismic: no-op, no result attached
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_code_experiment_loop.py -v`
Expected: FAIL (no `_run_code_experiment` / no `code_writer`/`sandbox_executor` attrs)

- [ ] **Step 3: Implement `_run_code_experiment` + wire deps**

In `backend/app/workflows/scientist_workflow.py`:
- Imports (top, near other agent imports):
```python
import hashlib
import json

from app.agents.code_writer_agent import CodeWriterAgent
from app.agents.fair_comparison_planner import FairComparisonPlanner
from app.schemas.code_experiment import (
    AcceptanceGate, CodeExperimentResult, ComparisonResult, DebugEntry,
    ExperimentSummary, IterEntry,
)
from app.tools.sandbox_executor import SandboxExecutor
```
- In `__init__` (after `self.repo_verifier = ...` / near other agent wiring):
```python
        self.code_writer = CodeWriterAgent(self.llm)
        self.fair_comparison_planner = FairComparisonPlanner()
        self.sandbox_executor = SandboxExecutor(
            self.settings.experiments_dir,
            timeout=self.settings.code_experiment_timeout_seconds,
        )
```
- Add the step method (near `_verify_baselines_auto`):
```python
    async def _run_code_experiment(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped code experiment (non-seismic)."
            return
        selected = _selected_hypothesis(run.hypotheses)
        sandbox_dir = self.settings.data_dir / "outputs" / run.run_id / "sandbox"
        fcp = self.fair_comparison_planner.plan()
        manifest = self._load_harness_manifest()
        max_rounds = int(manifest.get("max_repair_rounds", 3))
        iteration_log: list[IterEntry] = []
        debug_log: list[DebugEntry] = []
        source = await self.code_writer.arun(
            "initial", selected, run.experiment_plan, run_id=run.run_id)
        tests_pass = False
        last_stderr = None
        for rnd in range(1, max_rounds + 1):
            self.sandbox_executor.prepare(sandbox_dir, source)
            res = self.sandbox_executor.run(sandbox_dir, "tests.py")
            tests_pass = res.exit_code == 0
            last_stderr = None if tests_pass else res.stderr
            iteration_log.append(IterEntry(
                round=rnd,
                phase="initial" if rnd == 1 else "repair",
                model_py_hash=hashlib.md5(source.encode("utf-8")).hexdigest()[:8],
                tests_passed=tests_pass,
                traceback_summary=(last_stderr or "")[:300] or None,
            ))
            debug_log.append(DebugEntry(round=rnd, traceback_full=last_stderr, patch_diff=None))
            if tests_pass:
                break
            if rnd < max_rounds:
                source = await self.code_writer.arun(
                    "repair", selected, run.experiment_plan,
                    current_source=source, traceback=last_stderr, run_id=run.run_id)
        gate = AcceptanceGate(tests_pass=tests_pass)
        comparison = ComparisonResult()
        if not tests_pass:
            comparison.outcome = "failed"
            comparison.notes.append("micro repair exhausted; tests.py never passed")
        else:
            self.sandbox_executor.run(sandbox_dir, "train.py")
            metrics_p = sandbox_dir / "metrics.json"
            comp_p = sandbox_dir / "comparison.json"
            gate.metrics_generated = metrics_p.exists()
            gate.baseline_comparison_written = comp_p.exists()
            if gate.metrics_generated and gate.baseline_comparison_written:
                try:
                    comparison = ComparisonResult(**json.loads(comp_p.read_text(encoding="utf-8")))
                except Exception:
                    comparison.outcome = "failed"
                    comparison.notes.append("comparison.json malformed")
            else:
                comparison.outcome = "failed"
                comparison.notes.append("train.py failed; metrics/comparison not written")
        best = _best_metric(comparison)
        failure_reason = (comparison.notes[0] if comparison.outcome == "failed" and comparison.notes else None)
        run.code_experiment = CodeExperimentResult(
            model_py_source=source,
            fair_comparison_plan=fcp,
            acceptance_gate=gate,
            comparison=comparison,
            iteration_log=iteration_log,
            debug_log=debug_log,
            summary=ExperimentSummary(
                outcome=comparison.outcome,
                tests_pass=tests_pass,
                method_beats_baseline=comparison.method_beats_baseline,
                baseline_source=fcp.baseline_source,
                best_metric=best,
                failure_reason=failure_reason,
            ),
        )
        if run.steps:
            run.steps[-1].summary = (
                f"Code experiment: {comparison.outcome} "
                f"(tests_pass={tests_pass}, beats_baseline={comparison.method_beats_baseline}, "
                f"best_metric={best}).")

    def _load_harness_manifest(self) -> dict:
        path = self.settings.experiments_dir / "harness_manifest.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"max_repair_rounds": 3}
```
- Add module-level helper near `_selected_hypothesis`:
```python
def _best_metric(comparison: ComparisonResult) -> float | None:
    m = comparison.method_metrics or {}
    for key in ("accuracy", "macro_f1"):
        v = m.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None
```
- In `_run_after_evidence_review`, insert `code_experiment` between `experiment_design` and `report_writer` (seismic-only):
```python
        await self._step(run, "experiment_design", self._design_experiment)
        if run.domain == "seismic_event_classification":
            await self._step(run, "code_experiment", self._run_code_experiment)
        await self._step(run, "report_writer", self._write_report)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_code_experiment_loop.py -v`
Expected: PASS (5 tests: completed_positive / tests-fail-failed / fallback-negative / train-crash-failed / non-seismic-skip)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 8: LangGraph 接入（仅 seismic 真跑；非 seismic no-op）

**Files:**
- Modify: `backend/app/workflows/langgraph_workflow.py`
- Test: `backend/tests/test_s4_langgraph.py`

**Interfaces:**
- 加 `code_experiment` 节点（`_make_step_node`），把 `experiment_design → report_writer` 直连边改成 `experiment_design → code_experiment → report_writer`。
- `_run_code_experiment` 对非 seismic no-op（Task 7 已实现），所以非 seismic 也走该节点（同 `paper_classification` 模式），非 seismic step_names 仍含 `code_experiment`。
- 更新现有非 seismic langgraph step_names 断言：在 `experiment_design` 后插入 `code_experiment`。

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_s4_langgraph.py
import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.langgraph_workflow import LangGraphWorkflow


async def _noop_step(self, run) -> None:
    """Stub for heavy step methods. Bound via class-level monkeypatch so
    `self` is passed (instance-attribute functions would NOT bind self)."""
    return None


_STEP_METHODS = (
    "_plan", "_search_literature_with_langchain_tools",
    "_verify_citations_with_langchain_tools", "_build_evidence",
    "_mine_literature", "_classify_papers", "_profile_scientific_data",
    "_run_arena", "_extract_code_urls", "_discover_baselines_auto",
    "_verify_baselines_auto", "_design_experiment", "_run_code_experiment",
    "_generate_and_critique", "_write_report", "_verify_claims",
    "_revise_report_after_audit", "_translate_report", "_route_intent",
)


def _stub_steps(monkeypatch) -> None:
    for m in _STEP_METHODS:
        monkeypatch.setattr(LangGraphWorkflow, m, _noop_step)


def _completed_names(run: ResearchRun) -> list[str]:
    return [s.name for s in run.steps if s.status == "completed"]


@pytest.mark.asyncio
async def test_seismic_run_inserts_code_experiment_between_experiment_design_and_report(monkeypatch):
    _stub_steps(monkeypatch)
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    result = await wf.run(run)
    names = _completed_names(result)
    assert "code_experiment" in names
    assert names.index("code_experiment") > names.index("experiment_design")
    assert names.index("code_experiment") < names.index("report_writer")
    # seismic path runs arena, not hypothesis_debate
    assert "arena" in names
    assert "hypothesis_debate" not in names


@pytest.mark.asyncio
async def test_non_seismic_run_traverses_code_experiment_as_noop(monkeypatch):
    _stub_steps(monkeypatch)
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    run = ResearchRun(domain="energy_materials", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    result = await wf.run(run)
    names = _completed_names(result)
    # code_experiment is in the linear path (no-op for non-seismic), per the
    # paper_classification pattern — so the non-seismic step_names assertion in
    # test_langgraph_workflow_completes_sync_run must include it too.
    assert "code_experiment" in names
    assert names.index("code_experiment") > names.index("experiment_design")
    assert names.index("code_experiment") < names.index("report_writer")
    # non-seismic runs hypothesis_debate, not arena
    assert "hypothesis_debate" in names
    assert "arena" not in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s4_langgraph.py -v`
Expected: FAIL (no `code_experiment` node / edge)

- [ ] **Step 3: Wire the node + edge**

In `backend/app/workflows/langgraph_workflow.py` `_build_graph`:
- Add the node (near the arena/baseline nodes):
```python
        graph.add_node("code_experiment", self._make_step_node("code_experiment", "_run_code_experiment"))
```
- Replace the direct edge `graph.add_edge("experiment_design", "report_writer")` with:
```python
        graph.add_edge("experiment_design", "code_experiment")
        graph.add_edge("code_experiment", "report_writer")
```
- Update the existing non-seismic step_names assertion in `test_langgraph_workflow_completes_sync_run` (`backend/tests/test_langgraph_workflow.py`): insert `"code_experiment"` immediately after `"experiment_design"` in the expected `step_names` list.

> Note：`_LINEAR_STEPS` 不动（它只定义 add_node；边是显式 add_edge）。`code_experiment` 节点对非 seismic 调 `_run_code_experiment`，后者第一行 `if run.domain != "seismic_event_classification": ... return` 即 no-op，所以非 seismic 也会在 step_names 里出现 `code_experiment`（同 `paper_classification`）。

- [ ] **Step 4: Run tests to verify they pass + regression**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest tests/test_s4_langgraph.py tests/test_langgraph_workflow.py -v`
Expected: PASS (new s4 tests + updated existing langgraph test)

- [ ] **Step 5: Skip commit (local-only).**

---

### Task 9: 前端面板（CodePlan / CodeDebug / ExperimentResults）

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/components/workbench/CodePlanPanel.tsx`
- Create: `frontend/components/workbench/CodeDebugPanel.tsx`
- Create: `frontend/components/workbench/ExperimentResultsPanel.tsx`
- Modify: `frontend/components/workbench/Workbench.tsx`
- Test: manual.

**Interfaces:**
- `api.ts`：`Run` 加 `code_experiment?: CodeExperimentResult`；新增 `CodeExperimentResult`/`AcceptanceGate`/`ComparisonResult`/`FairComparisonPlan`/`IterEntry`/`DebugEntry`/`ExperimentSummary` 类型（字段对齐 `backend/app/schemas/code_experiment.py`）。
- `CodePlanPanel`：显示 `harness_version`/`model_family`/`baseline_source` + `fair_comparison_plan` + `model_py_source`（**默认折叠 / max-height + 滚动**，防长代码撑爆页面）。
- `CodeDebugPanel`：`iteration_log` 时间线（round/phase/tests_passed/traceback_summary）+ 选中轮的 `debug_log` traceback_full / patch_diff。
- `ExperimentResultsPanel`：method vs baseline metrics 表（accuracy/macro_f1/per_class_f1）+ outcome 徽章 + acceptance_gate 三项状态 + `summary.best_metric` + comparison.notes。
- `Workbench`：seismic 布局在 HypothesisArenaPanel/BaselineBoard 之后挂这三个面板（仅 `run.code_experiment` 存在时渲染）。

- [ ] **Step 1: Add types to `frontend/lib/api.ts`**

```typescript
export interface AcceptanceGate {
  tests_pass: boolean;
  metrics_generated: boolean;
  baseline_comparison_written: boolean;
  all_passed?: boolean;
}
export interface ComparisonResult {
  baseline_source: string;
  baseline_metrics: Record<string, number | Record<string, number>>;
  method_metrics: Record<string, number | Record<string, number>>;
  method_beats_baseline: boolean;
  outcome: "completed_positive" | "completed_negative" | "failed";
  notes: string[];
}
export interface FairComparisonPlan {
  method_name: string;
  baseline_source: string;
  split_strategy: string;
  metrics: string[];
  preprocessing: string;
}
export interface IterEntry {
  round: number;
  phase: "initial" | "repair";
  model_py_hash: string;
  tests_passed: boolean;
  traceback_summary?: string | null;
}
export interface DebugEntry {
  round: number;
  traceback_full?: string | null;
  patch_diff?: string | null;
}
export interface ExperimentSummary {
  outcome: "completed_positive" | "completed_negative" | "failed";
  tests_pass: boolean;
  method_beats_baseline: boolean;
  baseline_source: string;
  best_metric: number | null;
  failure_reason: string | null;
}
export interface CodeExperimentResult {
  harness_version: string;
  model_family: string;
  baseline_source: string;
  model_py_source: string;
  fair_comparison_plan: FairComparisonPlan;
  acceptance_gate: AcceptanceGate;
  comparison: ComparisonResult;
  iteration_log: IterEntry[];
  debug_log: DebugEntry[];
  summary: ExperimentSummary;
}
```
And add to the `Run` interface:
```typescript
  code_experiment?: CodeExperimentResult | null;
```

- [ ] **Step 2: CodePlanPanel (collapsible model.py)**

```tsx
// frontend/components/workbench/CodePlanPanel.tsx
import { useState } from "react";
import type { CodeExperimentResult } from "@/lib/api";

export function CodePlanPanel({ ce }: { ce: CodeExperimentResult }) {
  const [open, setOpen] = useState(false);
  const fcp = ce.fair_comparison_plan;
  return (
    <section className="panel">
      <h3>Code Plan</h3>
      <div className="kv">
        <span><strong>harness:</strong> {ce.harness_version}</span>
        <span><strong>model_family:</strong> {ce.model_family}</span>
        <span><strong>baseline_source:</strong> {ce.baseline_source}</span>
      </div>
      <div className="kv">
        <span><strong>split:</strong> {fcp.split_strategy}</span>
        <span><strong>metrics:</strong> {fcp.metrics.join(", ")}</span>
      </div>
      <p className="muted">{fcp.preprocessing}</p>
      <button className="link" onClick={() => setOpen(v => !v)}>
        {open ? "▾ hide model.py" : "▸ show model.py"}
      </button>
      {open && (
        <pre className="code-scroll" style={{ maxHeight: 360, overflow: "auto" }}>
{ce.model_py_source}
        </pre>
      )}
    </section>
  );
}
```

- [ ] **Step 3: CodeDebugPanel**

```tsx
// frontend/components/workbench/CodeDebugPanel.tsx
import { useState } from "react";
import type { CodeExperimentResult } from "@/lib/api";

export function CodeDebugPanel({ ce }: { ce: CodeExperimentResult }) {
  const [sel, setSel] = useState<number>(ce.debug_log[0]?.round ?? 0);
  const entry = ce.debug_log.find(d => d.round === sel);
  return (
    <section className="panel">
      <h3>Code Debug</h3>
      <ol className="timeline">
        {ce.iteration_log.map(it => (
          <li key={it.round} className={it.tests_passed ? "ok" : "err"}
              onClick={() => setSel(it.round)} style={{ cursor: "pointer" }}>
            <strong>R{it.round}</strong> {it.phase} · {it.tests_passed ? "PASS" : "FAIL"}
            <code> {it.model_py_hash}</code>
          </li>
        ))}
      </ol>
      {entry?.traceback_full && (
        <pre className="code-scroll" style={{ maxHeight: 320, overflow: "auto" }}>
{entry.traceback_full}
        </pre>
      )}
    </section>
  );
}
```

- [ ] **Step 4: ExperimentResultsPanel**

```tsx
// frontend/components/workbench/ExperimentResultsPanel.tsx
import type { CodeExperimentResult } from "@/lib/api";

const OUTCOME_BADGE: Record<string, string> = {
  completed_positive: "good",
  completed_negative: "warn",
  failed: "warn",
};

export function ExperimentResultsPanel({ ce }: { ce: CodeExperimentResult }) {
  const { comparison, acceptance_gate, summary } = ce;
  const bm = comparison.baseline_metrics as Record<string, number>;
  const mm = comparison.method_metrics as Record<string, number>;
  return (
    <section className="panel">
      <h3>Experiment Results</h3>
      <div className="badges">
        <span className={`badge ${OUTCOME_BADGE[comparison.outcome] ?? "warn"}`}>
          {comparison.outcome}
        </span>
        {summary.best_metric != null && (
          <span className="badge">best_metric {summary.best_metric.toFixed(3)}</span>
        )}
      </div>
      <table className="metrics-table">
        <thead><tr><th>metric</th><th>baseline</th><th>method</th></tr></thead>
        <tbody>
          <tr><td>accuracy</td><td>{bm.accuracy?.toFixed?.(3) ?? "-"}</td><td>{mm.accuracy?.toFixed?.(3) ?? "-"}</td></tr>
          <tr><td>macro_f1</td><td>{bm.macro_f1?.toFixed?.(3) ?? "-"}</td><td>{mm.macro_f1?.toFixed?.(3) ?? "-"}</td></tr>
        </tbody>
      </table>
      <ul className="muted">
        <li>tests_pass: {String(acceptance_gate.tests_pass)}</li>
        <li>metrics_generated: {String(acceptance_gate.metrics_generated)}</li>
        <li>baseline_comparison_written: {String(acceptance_gate.baseline_comparison_written)}</li>
      </ul>
      {comparison.notes.length > 0 && (
        <ul className="notes">{comparison.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
      )}
    </section>
  );
}
```

- [ ] **Step 5: Wire into Workbench seismic layout**

In `frontend/components/workbench/Workbench.tsx`, in the seismic version's panel list, after `<BaselineBoard ... />` (or `HypothesisArenaPanel`), add (only when `run.code_experiment` exists):

```tsx
{run.code_experiment && (
  <>
    <CodePlanPanel ce={run.code_experiment} />
    <CodeDebugPanel ce={run.code_experiment} />
    <ExperimentResultsPanel ce={run.code_experiment} />
  </>
)}
```
Add the corresponding imports at the top.

- [ ] **Step 6: Manual verification**

Open http://localhost:3000 → Seismic Expert → 启动一个 seismic discovery run。等 `code_experiment` 步完成后：
- CodePlanPanel 显示 harness manifest + fair plan；点开 `model.py` 折叠区看到 LLM 生成的源码（不撑爆页面，限高滚动）。
- CodeDebugPanel 看到 iteration 时间线（至少 R1 initial；若 LLM 一次过则 1 条；traceback 区空）。
- ExperimentResultsPanel 显示 outcome 徽章（completed_positive 或 negative）、method vs baseline accuracy/macro_f1 表、acceptance gate 三项 true。

- [ ] **Step 7: Skip commit (local-only).**

---

### Task 10: 验收

- [ ] **Step 1: Full backend suite**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q
```
Expected: all green incl. new s4 tests + regression (更新非 seismic langgraph step_names 断言含 `code_experiment`)。

- [ ] **Step 2: Live acceptance (real Qwen, seismic discovery run)**

Seismic run end-to-end：
1. `code_experiment` 步在 `experiment_design` 之后、`report_writer` 之前出现。
2. `data/outputs/{run_id}/sandbox/` 下有 `model.py`、`metrics.json`、`comparison.json`（若 tests 过）。
3. `run.code_experiment.summary.outcome` ∈ {completed_positive, completed_negative}（理想是 positive，但 negative 也算闭环成功——诚实输出）。
4. 前端 3 面板有内容；CodePlanPanel 的 model.py 折叠正常。
5. 报告 Experiment 段引用了 code experiment 的 metrics/comparison（S5 会增强，S4 至少不崩）。

- [ ] **Step 3: Skip commit (local-only).** Update `SESSION_HANDOFF.md` §2/§5 标记 S4 完成。

---

## S4 验收

- [ ] 全量测试绿（新增 ~26 个 s4 测试 + 更新 langgraph step_names 断言）。
- [ ] Live seismic run 产出 `code_experiment`，outcome 为 positive 或 negative（非 failed 即闭环跑通；failed 也诚实）。
- [ ] fallback 路径验证：若 Qwen 偶发失智，闭环仍产出骨架 model + completed_negative，不崩。

## 已知 S4 局限（留给后续）

- **macro ReAct 留 S5**：S4 不做"评估→改架构→重跑"；method 没打赢 baseline 直接 completed_negative，不自动改架构重试。S5 的 macro ReAct 接管（实验失败→诊断/修改/switchback + baseline 重搜）。
- **switchback 留 S5**：Top1 跑挂不切 Top2。
- **真实网络隔离留 S7**：S4 沙盒靠预装 deps + 命令白名单兜，无 OS 级网络隔离。
- **真实 STEAD 数据集留 S7**：S4 用 numpy 合成波形；S7 换真实子集 + torch CNN（`model_family: torch` 分支）。
- **verified_repo baseline 留 S7**：`baseline_source: verified_repo` 分支接口在，S4 不实现（跑 S3.5 verified repo 的 run_command）。
- **per_source_limit 截断（literature_router）**：S3.5 遗留小坑，S5 重搜循环时顺手修。
- **报告 Experiment 段**：S4 只保证 `run.code_experiment` 产出 + 不崩；把 metrics/comparison/iteration_log 正式写进 v3 报告字段是 S5 的报告增强范围。
