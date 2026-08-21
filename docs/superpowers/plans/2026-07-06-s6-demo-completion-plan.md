# TrustSci-Agent S6 Demo Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the local contest-demo development baseline and complete S6 with distinct research modes, safe experiment assistance, result analysis, compact V3 APIs, report provenance, and frontend support.

**Architecture:** Keep `ResearchRun` as the canonical state and preserve the existing `ScientistWorkflow`/`LangGraphWorkflow` inheritance boundary. Add focused schemas and result-analysis agents, route experiment assistance around code generation, expose a stable summary projection, and add defense-in-depth validation before generated code reaches the subprocess executor.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, LangChain Core, LangGraph, pytest, Next.js 16, React 19, TypeScript, scikit-learn.

**Execution constraint:** Keep every change in the current worktree. Do not create Git commits.

---

## File map

- `backend/app/schemas/experiment_assistance.py`: experiment-assistance input and result-analysis output contracts.
- `backend/app/schemas/v3.py`: compact demonstration summary response.
- `backend/app/agents/result_analysis_agents.py`: deterministic plus LLM-backed result evaluation, ablation analysis, and interpretation.
- `backend/app/tools/code_safety.py`: AST policy for generated `model.py`.
- `backend/app/workflows/scientist_workflow.py`: classic-mode execution and shared S6 step methods.
- `backend/app/workflows/langgraph_workflow.py`: mode-specific routing and S6 graph nodes.
- `backend/app/api/routes_runs.py`: assistance attachment and summary endpoints.
- `backend/app/schemas/run.py`: canonical state fields for S6 input and outputs.
- `backend/app/schemas/report.py` and `backend/app/agents/report_writer_agent.py`: provenance extensions.
- `backend/app/tools/sandbox_executor.py`: validation and isolated interpreter launch.
- `frontend/lib/api.ts`: matching S6 types and endpoint client.
- `frontend/components/workbench/ExperimentAssistancePanel.tsx`: structured assistance input.
- `frontend/components/workbench/ResultAnalysisPanel.tsx`: result evaluation, ablation, and interpretation output.
- `frontend/components/workbench/Workbench.tsx`: attach-before-start flow and panel composition.
- `.env.example`, `README.md`, `docs/ARCHITECTURE.md`: reproducible setup and accurate V3 documentation.
- `scripts/check_dev_env.py`: non-secret readiness diagnostics.

## Task 1: Restore a reproducible local baseline

**Files:**
- Create: `.env.example`
- Create: `scripts/check_dev_env.py`
- Create: `backend/tests/test_dev_environment.py`
- Modify: `README.md`

- [ ] **Step 1: Recreate the ignored virtual environment from the available Python 3.11 interpreter**

Run from the repository root:

```powershell
python -m venv --clear backend/.venv
& backend/.venv/Scripts/python.exe -m pip install --upgrade pip
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

Expected: all commands exit `0`; `backend/.venv/Scripts/python.exe --version` reports Python 3.11; imports of `reportlab`, `rapidfuzz`, `langgraph`, `numpy`, and `sklearn` succeed.

- [ ] **Step 2: Write the failing environment-contract tests**

Create `backend/tests/test_dev_environment.py`:

```python
from pathlib import Path

from scripts.check_dev_env import collect_status


ROOT = Path(__file__).resolve().parents[2]


def test_env_example_contains_every_runtime_key() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in (
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_BASE_URL",
        "QWEN_MODEL",
        "WORKFLOW_ENGINE",
        "DATA_DIR",
        "GITHUB_TOKEN",
        "NEXT_PUBLIC_API_BASE",
    ):
        assert f"{key}=" in text


def test_environment_check_never_returns_secret_values(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "secret-value")
    status = collect_status()
    rendered = repr(status)
    assert "secret-value" not in rendered
    assert status["qwen_configured"] is True
    assert "python" in status
```

- [ ] **Step 3: Run the tests and confirm the expected failure**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_dev_environment.py -q
```

Expected: collection fails because `scripts.check_dev_env` does not exist, or the environment-key assertion fails because `.env.example` is absent.

- [ ] **Step 4: Add safe example configuration**

Create `.env.example` with no live credentials:

```dotenv
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000
BROWSER_WORKER_PORT=8010
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
QWEN_TEMPERATURE=0.2
QWEN_TIMEOUT_SECONDS=60
QWEN_MAX_RETRIES=1
OPENALEX_EMAIL=
CROSSREF_EMAIL=
SEMANTIC_SCHOLAR_API_KEY=
MAX_PAPERS=6
DATA_DIR=data
MATERIALS_PROJECT_API_KEY=
GITHUB_TOKEN=
BROWSER_WORKER_URL=http://browser-worker:8010
WORKFLOW_ENGINE=langgraph
WATCHPACK_POLLING=true
CHOKIDAR_USEPOLLING=true
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

- [ ] **Step 5: Implement the non-secret environment checker**

Create `scripts/check_dev_env.py`:

```python
from __future__ import annotations

import importlib.util
import os
import shutil
import sys


REQUIRED_MODULES = (
    "fastapi",
    "pydantic",
    "reportlab",
    "rapidfuzz",
    "langgraph",
    "numpy",
    "sklearn",
)


def collect_status() -> dict[str, object]:
    return {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "modules": {name: importlib.util.find_spec(name) is not None for name in REQUIRED_MODULES},
        "node_available": shutil.which("node") is not None,
        "npm_available": shutil.which("npm") is not None,
        "docker_available": shutil.which("docker") is not None,
        "workflow_engine": os.getenv("WORKFLOW_ENGINE", "classic"),
        "qwen_configured": bool(os.getenv("DASHSCOPE_API_KEY", "").strip()),
    }


def main() -> int:
    status = collect_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    modules = status["modules"]
    return 0 if isinstance(modules, dict) and all(modules.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Update README setup commands**

Document both local PowerShell and Docker paths. State explicitly that no API key means deterministic fallback mode, that `WORKFLOW_ENGINE=langgraph` is the V3 route, and that Docker is optional for local backend/frontend development.

- [ ] **Step 7: Verify the repaired baseline**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_dev_environment.py -q
& backend/.venv/Scripts/python.exe scripts/check_dev_env.py
```

Expected: `2 passed`; checker exits `0`; output contains only the boolean `qwen_configured`, never a credential.

## Task 2: Add S6 schemas and canonical run state

**Files:**
- Create: `backend/app/schemas/experiment_assistance.py`
- Modify: `backend/app/schemas/run.py`
- Create: `backend/tests/test_s6_schemas.py`

- [ ] **Step 1: Write failing schema tests**

Create `backend/tests/test_s6_schemas.py`:

```python
import math

import pytest
from pydantic import ValidationError

from app.schemas.experiment_assistance import (
    AblationObservation,
    ExperimentAssistanceInput,
    MetricObservation,
    ResultEvaluation,
)
from app.schemas.run import ResearchConstraints, ResearchRun


def test_assistance_requires_metric_or_log() -> None:
    with pytest.raises(ValidationError):
        ExperimentAssistanceInput(objective="Compare two classifiers", method_summary="FFT model")


def test_metric_rejects_non_finite_values() -> None:
    with pytest.raises(ValidationError):
        MetricObservation(name="accuracy", value=math.inf)


def test_assistance_round_trip_on_research_run() -> None:
    supplied = ExperimentAssistanceInput(
        objective="Evaluate event classification",
        method_summary="FFT random forest",
        dataset_description="120 synthetic three-channel events",
        baseline_name="time-domain logistic regression",
        baseline_metrics=[MetricObservation(name="accuracy", value=0.80)],
        method_metrics=[MetricObservation(name="accuracy", value=0.86)],
        ablations=[AblationObservation(component="FFT features", metrics=[MetricObservation(name="accuracy", value=0.76)])],
    )
    run = ResearchRun(
        domain="seismic_event_classification",
        question="Analyze supplied experiment",
        mode="experiment_assistance",
        constraints=ResearchConstraints(),
        experiment_assistance=supplied,
        result_evaluation=ResultEvaluation(verdict="pass"),
    )
    restored = ResearchRun.model_validate_json(run.model_dump_json())
    assert restored.experiment_assistance.method_metrics[0].value == 0.86
    assert restored.result_evaluation.verdict == "pass"
```

- [ ] **Step 2: Verify tests fail before implementation**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_schemas.py -q
```

Expected: import error for `app.schemas.experiment_assistance`.

- [ ] **Step 3: Implement the schema module**

Create `backend/app/schemas/experiment_assistance.py`:

```python
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class MetricObservation(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    value: float
    unit: str | None = Field(default=None, max_length=40)
    split: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric value must be finite")
        return value


class AblationObservation(BaseModel):
    component: str = Field(min_length=1, max_length=200)
    metrics: list[MetricObservation] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)


class ExperimentAssistanceInput(BaseModel):
    objective: str = Field(min_length=3, max_length=2000)
    method_summary: str = Field(min_length=3, max_length=4000)
    source_code: str | None = Field(default=None, max_length=200_000)
    dataset_description: str = Field(default="", max_length=4000)
    baseline_name: str = Field(default="", max_length=300)
    baseline_metrics: list[MetricObservation] = Field(default_factory=list)
    method_metrics: list[MetricObservation] = Field(default_factory=list)
    ablations: list[AblationObservation] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list, max_length=100)
    author_notes: str = Field(default="", max_length=10_000)

    @model_validator(mode="after")
    def require_observation(self) -> "ExperimentAssistanceInput":
        if not self.method_metrics and not any(item.strip() for item in self.logs):
            raise ValueError("at least one method metric or experiment log is required")
        return self


class MetricDelta(BaseModel):
    name: str
    baseline: float | None = None
    method: float | None = None
    delta: float | None = None


class ResultEvaluation(BaseModel):
    verdict: Literal["pass", "partial", "fail"] = "partial"
    metric_deltas: list[MetricDelta] = Field(default_factory=list)
    supported_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    data_quality_warnings: list[str] = Field(default_factory=list)
    reasoning: str = ""


class AblationFinding(BaseModel):
    component: str
    effect: str
    metric_deltas: list[MetricDelta] = Field(default_factory=list)


class AblationAnalysis(BaseModel):
    coverage: Literal["complete", "partial", "missing"] = "missing"
    findings: list[AblationFinding] = Field(default_factory=list)
    missing_comparisons: list[str] = Field(default_factory=list)
    summary: str = ""


class ResultInterpretation(BaseModel):
    conclusions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    failure_explanation: str | None = None
    next_experiments: list[str] = Field(default_factory=list)
    evidence_boundary: str = ""
```

- [ ] **Step 4: Extend `ResearchRun` with optional S6 fields**

Import the four top-level S6 models and add:

```python
experiment_assistance: ExperimentAssistanceInput | None = None
result_evaluation: ResultEvaluation | None = None
ablation_analysis: AblationAnalysis | None = None
result_interpretation: ResultInterpretation | None = None
```

Place the input near `experiment_plan` and the three outputs immediately after `code_experiment` so serialized state remains readable.

- [ ] **Step 5: Run schema tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_schemas.py -q
```

Expected: `3 passed`.

## Task 3: Implement deterministic and LLM-backed result analysis

**Files:**
- Create: `backend/app/agents/result_analysis_agents.py`
- Create: `backend/tests/test_result_analysis_agents.py`

- [ ] **Step 1: Write failing deterministic-analysis tests**

Create `backend/tests/test_result_analysis_agents.py`:

```python
import pytest

from app.agents.result_analysis_agents import AblationAgent, ResultEvaluatorAgent, ResultInterpreterAgent
from app.config import Settings
from app.llm.registry import build_llm_client
from app.schemas.experiment_assistance import AblationObservation, ExperimentAssistanceInput, MetricObservation
from app.schemas.run import ResearchConstraints, ResearchRun


def assistance_run() -> ResearchRun:
    return ResearchRun(
        domain="seismic_event_classification",
        question="Analyze supplied results",
        mode="experiment_assistance",
        constraints=ResearchConstraints(),
        experiment_assistance=ExperimentAssistanceInput(
            objective="Beat the baseline",
            method_summary="FFT random forest",
            baseline_name="logistic regression",
            baseline_metrics=[MetricObservation(name="accuracy", value=0.80)],
            method_metrics=[MetricObservation(name="accuracy", value=0.86)],
            ablations=[AblationObservation(component="FFT features", metrics=[MetricObservation(name="accuracy", value=0.75)])],
        ),
    )


@pytest.mark.asyncio
async def test_result_evaluator_compares_shared_metrics_without_key() -> None:
    run = assistance_run()
    result = await ResultEvaluatorAgent(build_llm_client(Settings(dashscope_api_key=""))).arun(run)
    assert result.verdict == "pass"
    assert result.metric_deltas[0].delta == pytest.approx(0.06)
    assert result.supported_claims


@pytest.mark.asyncio
async def test_ablation_and_interpretation_are_bounded() -> None:
    run = assistance_run()
    llm = build_llm_client(Settings(dashscope_api_key=""))
    run.result_evaluation = await ResultEvaluatorAgent(llm).arun(run)
    run.ablation_analysis = await AblationAgent(llm).arun(run)
    result = await ResultInterpreterAgent(llm).arun(run)
    assert run.ablation_analysis.coverage == "partial"
    assert result.conclusions
    assert "user-provided" in result.evidence_boundary.lower()
```

- [ ] **Step 2: Run tests and confirm import failure**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_result_analysis_agents.py -q
```

Expected: import error for `result_analysis_agents`.

- [ ] **Step 3: Implement deterministic source normalization**

In `result_analysis_agents.py`, add private helpers:

```python
def _metric_map(items: list[MetricObservation]) -> dict[str, float]:
    return {item.name.strip().lower(): item.value for item in items}


def _source_metrics(run: ResearchRun) -> tuple[dict[str, float], dict[str, float], str]:
    if run.experiment_assistance is not None:
        supplied = run.experiment_assistance
        return _metric_map(supplied.baseline_metrics), _metric_map(supplied.method_metrics), "user-provided"
    if run.code_experiment is not None:
        comparison = run.code_experiment.comparison
        return dict(comparison.baseline_metrics), dict(comparison.method_metrics), "system-executed"
    return {}, {}, "unavailable"


def _fallback_evaluation(run: ResearchRun) -> ResultEvaluation:
    baseline, method, source = _source_metrics(run)
    deltas = [
        MetricDelta(name=name, baseline=baseline[name], method=method[name], delta=method[name] - baseline[name])
        for name in sorted(set(baseline) & set(method))
    ]
    positive = [item for item in deltas if item.delta is not None and item.delta > 0]
    negative = [item for item in deltas if item.delta is not None and item.delta < 0]
    verdict = "pass" if positive and not negative else "fail" if negative and not positive else "partial"
    warnings = [] if deltas else ["No directly comparable baseline and method metric was supplied."]
    supported = [f"{item.name} improved by {item.delta:.4f}." for item in positive]
    unsupported = ["The supplied observations do not establish generalization beyond this run."]
    return ResultEvaluation(
        verdict=verdict,
        metric_deltas=deltas,
        supported_claims=supported,
        unsupported_claims=unsupported,
        data_quality_warnings=warnings,
        reasoning=f"Deterministic comparison over {source} metrics.",
    )
```

- [ ] **Step 4: Implement the three agent classes using existing LCEL conventions**

Each class must expose `async def arun(self, run: ResearchRun)` and construct its deterministic result before making an LLM call. Bind the fallback model dump to `LLMClientRunnable`; normalize only known fields back into the target Pydantic model. Use agent audit names `result_evaluator`, `ablation_agent`, and `result_interpreter`.

The deterministic ablation behavior is:

```python
def _fallback_ablation(run: ResearchRun) -> AblationAnalysis:
    supplied = run.experiment_assistance
    if supplied is None or not supplied.ablations:
        return AblationAnalysis(
            coverage="missing",
            missing_comparisons=["No controlled component ablation was supplied."],
            summary="Ablation evidence is unavailable.",
        )
    method = _metric_map(supplied.method_metrics)
    findings = []
    for observation in supplied.ablations:
        ablated = _metric_map(observation.metrics)
        deltas = [
            MetricDelta(name=name, baseline=ablated[name], method=method[name], delta=method[name] - ablated[name])
            for name in sorted(set(method) & set(ablated))
        ]
        findings.append(AblationFinding(component=observation.component, effect="measured", metric_deltas=deltas))
    return AblationAnalysis(
        coverage="partial",
        findings=findings,
        missing_comparisons=["Only author-supplied ablations were available."],
        summary="Supplied ablations were compared with the complete method.",
    )
```

The deterministic interpretation must always label the evidence source:

```python
def _fallback_interpretation(run: ResearchRun) -> ResultInterpretation:
    evaluation = run.result_evaluation or ResultEvaluation()
    conclusions = list(evaluation.supported_claims)
    return ResultInterpretation(
        conclusions=conclusions or ["No performance improvement is established by comparable metrics."],
        limitations=list(evaluation.unsupported_claims) + list(evaluation.data_quality_warnings),
        failure_explanation="The supplied evidence does not pass the comparison gate." if evaluation.verdict == "fail" else None,
        next_experiments=["Repeat the comparison on an untouched event-level test split.", "Add controlled component ablations."],
        evidence_boundary="Conclusions are bounded to user-provided results and were not independently reproduced by TrustSci-Agent."
        if run.experiment_assistance is not None
        else "Conclusions are bounded to the system-executed local harness result.",
    )
```

- [ ] **Step 5: Run agent tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_result_analysis_agents.py -q
```

Expected: `2 passed` and no network request because the API key is empty.

## Task 4: Make all three workflow modes behaviorally distinct

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py`
- Modify: `backend/app/workflows/langgraph_workflow.py`
- Create: `backend/tests/test_s6_mode_routing.py`

- [ ] **Step 1: Write failing routing tests**

Create `backend/tests/test_s6_mode_routing.py`:

```python
import pytest

from app.config import Settings
from app.schemas.experiment_assistance import ExperimentAssistanceInput, MetricObservation
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.langgraph_workflow import LangGraphWorkflow


PIPELINE_METHODS = (
    "_route_intent", "_plan", "_search_literature_with_langchain_tools",
    "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
    "_classify_papers", "_profile_scientific_data", "_run_arena",
    "_run_novelty_check", "_extract_code_urls", "_discover_baselines_auto",
    "_verify_baselines_auto", "_evaluate_baseline_gate", "_re_search_literature",
    "_design_experiment", "_run_code_experiment", "_run_macro_react",
    "_evaluate_results", "_analyze_ablations", "_interpret_results",
    "_write_report", "_verify_claims", "_revise_report_after_audit", "_translate_report",
)


def assistance_run() -> ResearchRun:
    return ResearchRun(
        domain="seismic_event_classification",
        question="Analyze supplied experiment",
        mode="experiment_assistance",
        constraints=ResearchConstraints(),
        experiment_assistance=ExperimentAssistanceInput(
            objective="Compare classifiers",
            method_summary="FFT random forest",
            baseline_metrics=[MetricObservation(name="accuracy", value=0.80)],
            method_metrics=[MetricObservation(name="accuracy", value=0.86)],
        ),
    )


def recorder(name: str, calls: list[str]):
    async def inner(self, run):
        calls.append(name)
    return inner


@pytest.mark.asyncio
async def test_experiment_assistance_skips_arena_and_code_execution(monkeypatch):
    workflow = LangGraphWorkflow(Settings(dashscope_api_key="", workflow_engine="langgraph"))
    calls: list[str] = []
    for method in PIPELINE_METHODS:
        monkeypatch.setattr(LangGraphWorkflow, method, recorder(method, calls), raising=False)

    run = assistance_run()
    await workflow.run(run)

    assert "_run_arena" not in calls
    assert "_run_code_experiment" not in calls
    assert "_run_macro_react" not in calls
    assert calls.index("_evaluate_results") < calls.index("_write_report")


@pytest.mark.asyncio
async def test_idea_refinement_runs_idea_intake_before_planning(monkeypatch):
    workflow = LangGraphWorkflow(Settings(dashscope_api_key="", workflow_engine="langgraph"))
    calls: list[str] = []
    for method in PIPELINE_METHODS:
        if method != "_route_intent":
            monkeypatch.setattr(LangGraphWorkflow, method, recorder(method, calls), raising=False)
    run = ResearchRun(
        domain="seismic_event_classification",
        question="Refine an FFT-based earthquake classifier idea",
        mode="idea_refinement",
        constraints=ResearchConstraints(),
    )
    await workflow.run(run)
    names = [step.name for step in run.steps if step.status == "completed"]
    assert run.idea_brief is not None
    assert names.index("intent_router") < names.index("planner")
    assert names.index("planner") < names.index("arena")
    assert names.index("arena") < names.index("result_evaluation")
```

- [ ] **Step 2: Run routing tests and confirm missing S6 step failures**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_mode_routing.py -q
```

Expected: failures because result-analysis methods and graph nodes do not exist and experiment assistance still reaches the common pipeline.

- [ ] **Step 3: Add shared S6 workflow methods**

Instantiate the three agents in `ScientistWorkflow.__init__`, then add:

```python
async def _evaluate_results(self, run: ResearchRun) -> None:
    run.result_evaluation = await self.result_evaluator.arun(run)


async def _analyze_ablations(self, run: ResearchRun) -> None:
    run.ablation_analysis = await self.ablation_agent.arun(run)


async def _interpret_results(self, run: ResearchRun) -> None:
    run.result_interpretation = await self.result_interpreter.arun(run)


async def _run_result_analysis(self, run: ResearchRun) -> None:
    await self._step(run, "result_evaluation", self._evaluate_results)
    await self._step(run, "ablation_analysis", self._analyze_ablations)
    await self._step(run, "result_interpretation", self._interpret_results)
```

- [ ] **Step 4: Split the classic workflow path**

At the beginning of `_run_after_evidence_review`, handle experiment assistance by profiling data, running result analysis, writing and auditing the report, and returning before paper classification, Arena, experiment design, code experiment, or macro ReAct. For discovery and idea refinement, run result analysis immediately after the existing experiment/macro path and before report writing.

- [ ] **Step 5: Add LangGraph result-analysis nodes and routing**

In `_build_graph`:

```python
graph.add_node("result_evaluation", self._make_step_node("result_evaluation", "_evaluate_results"))
graph.add_node("ablation_analysis", self._make_step_node("ablation_analysis", "_analyze_ablations"))
graph.add_node("result_interpretation", self._make_step_node("result_interpretation", "_interpret_results"))
graph.add_edge("result_evaluation", "ablation_analysis")
graph.add_edge("ablation_analysis", "result_interpretation")
graph.add_edge("result_interpretation", "report_writer")
```

Change the macro route target from `report_writer` to `result_evaluation`. Extend `_route_after_data_profile` to return `result_evaluation` when `run.mode == "experiment_assistance"`; otherwise preserve the seismic Arena/non-seismic hypothesis behavior. Keep idea refinement on the Arena path for the seismic domain, with its `IdeaBrief` produced during intent routing.

- [ ] **Step 6: Run routing and existing cycle tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_mode_routing.py backend/tests/test_s5_langgraph_cycles.py backend/tests/test_workflow_classic_s5.py -q
```

Expected: all selected tests pass; existing S5 loop caps remain unchanged.

## Task 5: Add assistance attachment and compact V3 summary APIs

**Files:**
- Create: `backend/app/schemas/v3.py`
- Modify: `backend/app/api/routes_runs.py`
- Create: `backend/tests/test_s6_api.py`

- [ ] **Step 1: Write failing endpoint tests**

Create `backend/tests/test_s6_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.code_experiment import CodeExperimentResult, ComparisonResult
from app.schemas.common import RunStatus
from app.schemas.experiment_assistance import ResultEvaluation
from app.schemas.feedback_loop import BaselineGateStatus, NoveltyVerdict
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.in_memory import run_store


client = TestClient(app)


def test_attach_experiment_assistance_before_start():
    created = client.post("/api/runs", json={
        "domain": "seismic_event_classification",
        "question": "Analyze my run",
        "mode": "experiment_assistance",
    }).json()
    response = client.post(f"/api/runs/{created['run_id']}/experiment-assistance", json={
        "objective": "Compare classifiers",
        "method_summary": "FFT random forest",
        "baseline_metrics": [{"name": "accuracy", "value": 0.8}],
        "method_metrics": [{"name": "accuracy", "value": 0.86}],
    })
    assert response.status_code == 200
    assert response.json()["experiment_assistance"]["objective"] == "Compare classifiers"


def test_attach_rejects_wrong_mode_and_running_run():
    discovery = client.post("/api/runs", json={"question": "q", "mode": "discovery"}).json()
    payload = {
        "objective": "Compare classifiers",
        "method_summary": "FFT random forest",
        "method_metrics": [{"name": "accuracy", "value": 0.86}],
    }
    wrong_mode = client.post(f"/api/runs/{discovery['run_id']}/experiment-assistance", json=payload)
    assert wrong_mode.status_code == 409

    created = client.post("/api/runs", json={"question": "q", "mode": "experiment_assistance"}).json()
    run = run_store.get(created["run_id"])
    assert run is not None
    run.status = RunStatus.running
    run_store.save(run)
    running = client.post(f"/api/runs/{run.run_id}/experiment-assistance", json=payload)
    assert running.status_code == 409
    assert run_store.get(run.run_id).experiment_assistance is None


def test_v3_summary_contains_stable_demo_fields():
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        mode="discovery",
        constraints=ResearchConstraints(),
        status=RunStatus.completed,
        current_stage="completed",
        progress=1.0,
        novelty_verdict=NoveltyVerdict(verdict="similar_work", reasoning="bounded novelty"),
        baseline_gate_status=BaselineGateStatus(comparison_grade="degraded"),
        code_experiment=CodeExperimentResult(
            comparison=ComparisonResult(
                baseline_metrics={"accuracy": 0.8},
                method_metrics={"accuracy": 0.86},
                outcome="completed_positive",
            )
        ),
        result_evaluation=ResultEvaluation(verdict="pass"),
        novelty_round=1,
        re_search_round=2,
        macro_round=1,
        switchback_used=False,
    )
    run_store.create(run)
    response = client.get(f"/api/runs/{run.run_id}/v3-summary")
    assert response.status_code == 200
    assert set(response.json()) == {
        "run_id", "mode", "status", "current_stage", "progress",
        "selected_hypothesis", "novelty", "baseline", "experiment",
        "result_evaluation", "loop_counters", "warnings", "report_ready",
    }
    assert response.json()["loop_counters"] == {
        "novelty_round": 1,
        "re_search_round": 2,
        "macro_round": 1,
        "switchback_used": False,
    }
```

- [ ] **Step 2: Confirm endpoints return 404 before implementation**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_api.py -q
```

Expected: endpoint assertions fail with `404`.

- [ ] **Step 3: Define the compact response schema**

Create `backend/app/schemas/v3.py`:

```python
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.experiment_assistance import ResultEvaluation


class V3RunSummary(BaseModel):
    run_id: str
    mode: str
    status: str
    current_stage: str
    progress: float
    selected_hypothesis: dict[str, Any] | None = None
    novelty: dict[str, Any] | None = None
    baseline: dict[str, Any] | None = None
    experiment: dict[str, Any] | None = None
    result_evaluation: ResultEvaluation | None = None
    loop_counters: dict[str, int | bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    report_ready: bool = False
```

- [ ] **Step 4: Implement attach semantics**

Add `POST /{run_id}/experiment-assistance` with `ExperimentAssistanceInput` as the body and `ResearchRun` as the response. Return `404` for a missing run, `409` unless mode is `experiment_assistance`, and `409` unless status is `created`. Save the run and write its workspace snapshot after attaching input.

- [ ] **Step 5: Implement summary projection**

Add a pure `_v3_summary(run)` helper and `GET /{run_id}/v3-summary`. Do not expose source code or full tracebacks. Populate warnings from `run.errors`, baseline insufficiency reasons, result data-quality warnings, and a missing-Qwen warning only when it is relevant to the display. `report_ready` is `True` only when `run.report` exists and status is completed.

- [ ] **Step 6: Run API tests and existing route tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_api.py backend/tests/test_api_routes.py backend/tests/test_baselines_api.py -q
```

Expected: all selected tests pass.

## Task 6: Extend report provenance and scientific-result boundaries

**Files:**
- Modify: `backend/app/schemas/report.py`
- Modify: `backend/app/agents/report_writer_agent.py`
- Modify: `backend/app/workflows/scientist_workflow.py`
- Create: `backend/tests/test_s6_report_provenance.py`

- [ ] **Step 1: Write failing provenance tests**

Create an experiment-assistance run with result evaluation, ablation analysis, and interpretation, call the deterministic report writer, and assert:

```python
assert provenance.arena_report == {}
assert provenance.baseline_provenance["source"] == "user-provided"
assert provenance.ablation_report["coverage"] == "partial"
assert provenance.result_support_judgment["verdict"] == "pass"
assert "not independently reproduced" in report.english_report.results.executed_results.lower()
```

Add a discovery-run assertion that `experiment_iteration_log` and `code_debug_log` are derived from `CodeExperimentResult` without storing unrestricted full tracebacks.

- [ ] **Step 2: Run the test and confirm missing fields**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_report_provenance.py -q
```

Expected: Pydantic attribute errors for the new provenance fields.

- [ ] **Step 3: Extend `SystemProvenance`**

Add these defaulted dictionaries/lists:

```python
arena_report: dict[str, Any] = Field(default_factory=dict)
baseline_provenance: dict[str, Any] = Field(default_factory=dict)
experiment_iteration_log: list[dict[str, Any]] = Field(default_factory=list)
code_debug_log: list[dict[str, Any]] = Field(default_factory=list)
ablation_report: dict[str, Any] = Field(default_factory=dict)
result_support_judgment: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Populate provenance from run state**

Extend `_system_provenance` so every field is a projection of existing state. For debug entries, retain `round`, a traceback summary capped at 500 characters, and whether a patch exists; omit `traceback_full` and raw patch text. For assistance mode, set baseline source to `user-provided` and include its name and metric values. For system execution, use `fair_comparison_plan` and `comparison`.

- [ ] **Step 5: Enforce user-provided result wording**

When `run.experiment_assistance` exists, the formal executed-results section must begin with a bounded sentence equivalent to:

```text
The following measurements were supplied by the user and were not independently reproduced by TrustSci-Agent.
```

Then summarize only metrics present in the input and the structured result evaluation. Expected validation outcomes remain separate.

- [ ] **Step 6: Run report tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_report_provenance.py backend/tests/test_report_writer_agent.py backend/tests/test_report_translator_agent.py backend/tests/test_report_reviser_agent.py -q
```

Expected: all selected tests pass and existing bilingual report behavior remains intact.

## Task 7: Harden generated-code execution for the local demo

**Files:**
- Create: `backend/app/tools/code_safety.py`
- Modify: `backend/app/tools/sandbox_executor.py`
- Create: `backend/tests/test_code_safety.py`
- Modify: `backend/tests/test_sandbox_executor.py`

- [ ] **Step 1: Write failing AST policy tests**

Create `backend/tests/test_code_safety.py`:

```python
import pytest

from app.tools.code_safety import UnsafeGeneratedCode, validate_generated_model


def test_allows_numpy_and_sklearn_model() -> None:
    validate_generated_model("""
import numpy as np
from sklearn.linear_model import LogisticRegression
class SeismicModel:
    def fit(self, X, y):
        self.model = LogisticRegression().fit(X.reshape(len(X), -1), y)
        return self
    def predict(self, X):
        return self.model.predict(X.reshape(len(X), -1))
""")


@pytest.mark.parametrize("source", [
    "import os\nos.system('whoami')",
    "import socket\nsocket.create_connection(('example.com', 80))",
    "open('secret.txt').read()",
    "__import__('subprocess').run(['whoami'])",
    "eval('1 + 1')",
])
def test_rejects_dangerous_generated_code(source: str) -> None:
    with pytest.raises(UnsafeGeneratedCode):
        validate_generated_model(source)
```

- [ ] **Step 2: Confirm module import failure**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_code_safety.py -q
```

Expected: import error for `code_safety`.

- [ ] **Step 3: Implement AST validation**

Create `backend/app/tools/code_safety.py`:

```python
from __future__ import annotations

import ast


DENIED_MODULES = {
    "ctypes", "httpx", "importlib", "multiprocessing", "os", "pathlib",
    "pip", "requests", "shutil", "socket", "subprocess", "sys", "urllib",
}
DENIED_CALLS = {"__import__", "compile", "eval", "exec", "input", "open"}


class UnsafeGeneratedCode(ValueError):
    pass


def validate_generated_model(source: str) -> None:
    try:
        tree = ast.parse(source, filename="model.py")
    except SyntaxError as exc:
        raise UnsafeGeneratedCode(f"model.py syntax error: {exc.msg}") from exc
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in DENIED_MODULES:
                    violations.append(f"denied import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in DENIED_MODULES:
                violations.append(f"denied import: {node.module}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in DENIED_CALLS:
            violations.append(f"denied call: {node.func.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            violations.append(f"denied dunder attribute: {node.attr}")
    if violations:
        raise UnsafeGeneratedCode("; ".join(sorted(set(violations))))
```

- [ ] **Step 4: Validate before writing and launch with an isolated bootstrap**

In `SandboxExecutor.prepare`, call `validate_generated_model(model_py_source)` before creating or changing the sandbox directory. In `run`, replace the direct script command with:

```python
bootstrap = (
    "import runpy,sys;"
    "sys.path.insert(0, '.');"
    f"runpy.run_path({script!r}, run_name='__main__')"
)
command = [sys.executable, "-I", "-c", bootstrap]
safe_env = {
    key: value
    for key, value in os.environ.items()
    if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PYTHONIOENCODING"}
}
safe_env["PYTHONIOENCODING"] = "utf-8"
```

Pass `env=safe_env` to `subprocess.run`. Keep the existing whitelist and timeout.

- [ ] **Step 5: Convert policy rejection into a normal experiment failure**

At the `ScientistWorkflow` call site that prepares the sandbox, catch `UnsafeGeneratedCode`, append a debug/iteration entry containing the short policy message, and let the micro repair loop request a corrected `model.py`. Never write rejected source into an executable sandbox.

- [ ] **Step 6: Run security and harness tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_code_safety.py backend/tests/test_sandbox_executor.py backend/tests/test_code_experiment_loop.py backend/tests/test_macro_react.py -q
```

Expected: all selected tests pass; fixed harness scripts still import local `data.py` and `model.py` under isolated mode.

## Task 8: Add frontend experiment-assistance input and result analysis

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/components/workbench/ExperimentAssistancePanel.tsx`
- Create: `frontend/components/workbench/ResultAnalysisPanel.tsx`
- Modify: `frontend/components/workbench/ResearchConsole.tsx`
- Modify: `frontend/components/workbench/Workbench.tsx`
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Add exact TypeScript API contracts**

Mirror the backend models with:

```typescript
export type MetricObservation = {
  name: string;
  value: number;
  unit?: string | null;
  split?: string | null;
  notes?: string | null;
};

export type ExperimentAssistanceInput = {
  objective: string;
  method_summary: string;
  source_code?: string | null;
  dataset_description: string;
  baseline_name: string;
  baseline_metrics: MetricObservation[];
  method_metrics: MetricObservation[];
  ablations: Array<{ component: string; metrics: MetricObservation[]; notes?: string | null }>;
  logs: string[];
  author_notes: string;
};
```

Add optional S6 fields to `ResearchRun` and implement:

```typescript
export async function attachExperimentAssistance(runId: string, payload: ExperimentAssistanceInput) {
  return request<ResearchRun>(`/api/runs/${runId}/experiment-assistance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}
```

- [ ] **Step 2: Add a controlled input panel**

`ExperimentAssistancePanel` receives `value` and `onChange`. Provide fields for objective, method summary, dataset, baseline name, baseline/method metric name and numeric value, logs, author notes, and optional source code. Accept local `.json`, `.txt`, `.log`, and `.py` files using `File.text()` and reject files larger than 200 KB in the UI. The component does not call the API directly.

- [ ] **Step 3: Add the output panel**

`ResultAnalysisPanel` renders verdict, metric deltas, supported and unsupported claims, data-quality warnings, ablation coverage/findings, conclusions, limitations, evidence boundary, and next experiments. Render nothing when all three S6 outputs are absent.

- [ ] **Step 4: Attach input before starting**

Extend `ConsoleDraft` with a default assistance payload. In `handleStart`, after `createRun` and before `startRun`:

```typescript
let ready = created;
if (draft.researchMode === "experiment_assistance") {
  ready = await attachExperimentAssistance(created.run_id, draft.experimentAssistance);
}
setRun(ready);
const started = await startRun(ready.run_id);
```

If attachment throws, surface the API error and leave the created run unstarted.

- [ ] **Step 5: Compose panels by mode**

Show the input panel only when the selected draft mode is experiment assistance. Show `ResultAnalysisPanel` for any run with S6 outputs. Do not remove existing code experiment, feedback loop, evidence, or report panels.

- [ ] **Step 6: Build the frontend**

Run:

```powershell
Set-Location frontend
npm run build
```

Expected: Next.js production build and TypeScript checks exit `0`.

## Task 9: Update architecture docs and run full verification

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/API.md`
- Modify: `SESSION_HANDOFF.md`
- Create: `backend/tests/test_s6_smoke.py`

- [ ] **Step 1: Add a deterministic S6 smoke test**

Create a FastAPI test that creates an experiment-assistance run, attaches baseline/method metrics, calls `run-sync`, and asserts:

```python
assert body["status"] == "completed"
assert body["code_experiment"] is None
assert body["result_evaluation"]["verdict"] in {"pass", "partial", "fail"}
assert body["ablation_analysis"] is not None
assert body["result_interpretation"]["evidence_boundary"]
assert body["report"]["system_provenance"]["result_support_judgment"]
```

Stub external literature clients so the smoke test is deterministic and offline.

- [ ] **Step 2: Update current documentation**

Document:

- seismic V3 as the primary contest route;
- the three distinct modes and their exact behavior;
- deterministic fallback versus configured Qwen operation;
- the two new S6 endpoints;
- generated-code safety limitations;
- synthetic seismic data limitations;
- current local PowerShell commands;
- S6 completion status and S7 remaining work.

Remove stale claims that the first demo is only energy materials or that the workflow is only the old linear agent chain.

- [ ] **Step 3: Run the complete backend suite**

Run from the repository root:

```powershell
& backend/.venv/Scripts/python.exe -m pytest -q
```

Expected: exit `0` with zero failed and zero collection errors. Record the exact passing count in `SESSION_HANDOFF.md` only after this command succeeds.

- [ ] **Step 4: Run the production frontend build**

Run:

```powershell
Set-Location frontend
npm run build
```

Expected: exit `0`, successful TypeScript check, and static `/` route generation.

- [ ] **Step 5: Run explicit demo readiness checks**

Run:

```powershell
Set-Location ..
& backend/.venv/Scripts/python.exe scripts/check_dev_env.py
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_smoke.py backend/tests/test_code_safety.py -q
git status --short
```

Expected: environment checker exits `0`; smoke and safety tests pass; Git status shows local changes but no created commit.

- [ ] **Step 6: Review the final diff for scope and secrets**

Run:

```powershell
git diff --check
git diff --stat
git grep -n "DASHSCOPE_API_KEY=" -- ':!*.example' ':!.env'
```

Expected: `git diff --check` has no whitespace errors; no live API key appears in tracked files; changes are limited to baseline repair, S6 implementation, tests, and documentation.
