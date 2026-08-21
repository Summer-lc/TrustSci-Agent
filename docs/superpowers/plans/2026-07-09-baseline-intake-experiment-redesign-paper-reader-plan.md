# Baseline Intake, Experiment Redesign, and Paper Reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace automatic baseline mining with explicit baseline intake, route poor executable results through experiment redesign, and add a lightweight paper reader to the frontend literature view.

**Architecture:** `ResearchRun` remains the single state object. Backend changes add focused schemas, API attach endpoints, workflow nodes, and report provenance fields; frontend changes add pre-run baseline strategy input and selected-paper reading state. Legacy baseline discovery code remains in place but leaves the main workflow route.

**Tech Stack:** FastAPI, Pydantic v2, LangGraph, pytest, Next.js/React/TypeScript.

**User constraint:** Do not create git commits. All changes stay in the local worktree.

---

## File Structure

- Create `backend/app/schemas/baseline_intake.py`: baseline strategy, manual baseline payload, normalized baseline intake.
- Modify `backend/app/schemas/run.py`: add baseline and redesign state fields.
- Modify `backend/app/schemas/report.py`: existing provenance model already has `baseline_provenance`; keep using that field.
- Create `backend/app/agents/baseline_intake_agent.py`: normalize manual/AI/none strategy into `BaselineIntake`.
- Create `backend/app/agents/experiment_redesign_agent.py`: revise `ExperimentPlan` after a completed poor result.
- Modify `backend/app/api/routes_runs.py`: add `POST /api/runs/{run_id}/baseline-intake`; include new state in `v3-summary`.
- Modify `backend/app/workflows/scientist_workflow.py`: add baseline intake, experiment result gate, experiment redesign methods; change classic path.
- Modify `backend/app/workflows/langgraph_workflow.py`: remove main-path baseline discovery edges; add baseline intake and experiment redesign routing.
- Modify `backend/app/agents/report_writer_agent.py`: prefer `run.baseline_intake` in provenance.
- Modify `frontend/lib/api.ts`: add TS types and `attachBaselineIntake`.
- Create `frontend/components/workbench/BaselineIntakePanel.tsx`: pre-run baseline strategy form.
- Modify `frontend/components/workbench/BaselineBoard.tsx`: display normalized baseline intake as primary status.
- Modify `frontend/components/workbench/LiteratureBoard.tsx`: make paper selection explicit.
- Create `frontend/components/workbench/PaperReaderPanel.tsx`: lightweight metadata/PDF reader.
- Modify `frontend/components/workbench/Workbench.tsx`: store baseline draft, attach intake before start, render paper reader.
- Add backend tests:
  - `backend/tests/test_baseline_intake_schemas.py`
  - `backend/tests/test_baseline_intake_api.py`
  - `backend/tests/test_baseline_intake_agent.py`
  - `backend/tests/test_experiment_redesign.py`
  - update `backend/tests/test_s4_langgraph.py`, `backend/tests/test_s5_langgraph_cycles.py`, `backend/tests/test_workflow_classic_s5.py`, and provenance tests.

---

### Task 1: Baseline Intake Schemas

**Files:**
- Create: `backend/app/schemas/baseline_intake.py`
- Modify: `backend/app/schemas/run.py`
- Test: `backend/tests/test_baseline_intake_schemas.py`

- [ ] **Step 1: Write failing schema tests**

Create `backend/tests/test_baseline_intake_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.baseline_intake import (
    BaselineIntake,
    BaselineIntakeRequest,
    ManualBaselineInput,
    MetricObservation,
)
from app.schemas.run import ResearchConstraints, ResearchRun


def test_manual_baseline_request_accepts_metrics() -> None:
    payload = BaselineIntakeRequest(
        strategy="manual_upload",
        manual=ManualBaselineInput(
            name="User RF baseline",
            description="RandomForest baseline from prior experiment.",
            dataset_description="Synthetic seismic demo split.",
            metrics=[MetricObservation(name="accuracy", value=0.81, split="test")],
            repository_url="https://example.com/baseline",
            run_command="python train_baseline.py",
            notes="Provided by user before run.",
        ),
    )
    assert payload.strategy == "manual_upload"
    assert payload.manual.metrics[0].value == 0.81


def test_manual_baseline_requires_useful_content() -> None:
    with pytest.raises(ValidationError):
        BaselineIntakeRequest(
            strategy="manual_upload",
            manual=ManualBaselineInput(name="b"),
        )


def test_ai_generated_and_none_do_not_require_manual_payload() -> None:
    assert BaselineIntakeRequest(strategy="ai_generated").manual is None
    assert BaselineIntakeRequest(strategy="none").manual is None


def test_metric_rejects_non_finite_value() -> None:
    with pytest.raises(ValidationError):
        MetricObservation(name="accuracy", value=float("nan"))


def test_research_run_round_trips_baseline_fields() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="manual_upload",
        baseline_intake=BaselineIntake(
            strategy="manual_upload",
            source_type="manual_upload",
            trust_level="user_provided",
            name="User baseline",
            description="Provided baseline.",
            metrics=[MetricObservation(name="accuracy", value=0.8)],
            limitations=[],
            provenance_notes=["attached before start"],
        ),
    )
    restored = ResearchRun.model_validate_json(run.model_dump_json())
    assert restored.baseline_strategy == "manual_upload"
    assert restored.baseline_intake.name == "User baseline"
```

- [ ] **Step 2: Run the failing schema tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_baseline_intake_schemas.py -q
```

Expected: FAIL because `app.schemas.baseline_intake` does not exist.

- [ ] **Step 3: Add baseline intake schemas**

Create `backend/app/schemas/baseline_intake.py`:

```python
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


BaselineStrategy = Literal["manual_upload", "ai_generated", "none"]


class MetricObservation(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    value: float
    unit: str | None = None
    split: str | None = None
    notes: str | None = None

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric value must be finite")
        return value


class ManualBaselineInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    code_text: str | None = Field(default=None, max_length=200_000)
    repository_url: str | None = Field(default=None, max_length=2000)
    run_command: str | None = Field(default=None, max_length=1000)
    dataset_description: str = ""
    metrics: list[MetricObservation] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def require_useful_content(self):
        has_text = any(
            bool((value or "").strip())
            for value in (self.description, self.code_text, self.repository_url, self.run_command, self.notes)
        )
        if not self.metrics and not has_text:
            raise ValueError("manual baseline requires metrics, code, repository, command, description, or notes")
        return self


class BaselineIntakeRequest(BaseModel):
    strategy: BaselineStrategy
    manual: ManualBaselineInput | None = None

    @model_validator(mode="after")
    def validate_strategy_payload(self):
        if self.strategy == "manual_upload" and self.manual is None:
            raise ValueError("manual baseline payload is required for manual_upload strategy")
        if self.strategy != "manual_upload" and self.manual is not None:
            raise ValueError("manual baseline payload is only allowed for manual_upload strategy")
        return self


class BaselineIntake(BaseModel):
    strategy: BaselineStrategy
    source_type: Literal["manual_upload", "ai_generated", "unavailable"]
    trust_level: Literal["user_provided", "runnable_demo", "insufficient"]
    name: str = ""
    description: str = ""
    metrics: list[MetricObservation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance_notes: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Add fields to `ResearchRun`**

Modify `backend/app/schemas/run.py` imports:

```python
from app.schemas.baseline_intake import BaselineIntake, BaselineIntakeRequest, BaselineStrategy
```

Add fields near `baseline_candidates`:

```python
    baseline_strategy: BaselineStrategy = "none"
    manual_baseline: BaselineIntakeRequest | None = None
    baseline_intake: BaselineIntake | None = None
```

- [ ] **Step 5: Run schema tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_baseline_intake_schemas.py -q
```

Expected: PASS.

---

### Task 2: Baseline Intake API

**Files:**
- Modify: `backend/app/api/routes_runs.py`
- Test: `backend/tests/test_baseline_intake_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_baseline_intake_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_attach_manual_baseline_before_start() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q"},
    ).json()
    response = client.post(
        f"/api/runs/{created['run_id']}/baseline-intake",
        json={
            "strategy": "manual_upload",
            "manual": {
                "name": "User baseline",
                "description": "Prior RF baseline.",
                "metrics": [{"name": "accuracy", "value": 0.8}],
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["baseline_strategy"] == "manual_upload"
    assert body["manual_baseline"]["manual"]["name"] == "User baseline"


def test_attach_ai_generated_baseline_before_start() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q"},
    ).json()
    response = client.post(
        f"/api/runs/{created['run_id']}/baseline-intake",
        json={"strategy": "ai_generated"},
    )
    assert response.status_code == 200
    assert response.json()["baseline_strategy"] == "ai_generated"


def test_attach_baseline_404() -> None:
    response = client.post("/api/runs/run_missing/baseline-intake", json={"strategy": "none"})
    assert response.status_code == 404


def test_attach_baseline_after_start_returns_409() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q"},
    ).json()
    started = client.post(f"/api/runs/{created['run_id']}/start")
    assert started.status_code == 200
    response = client.post(
        f"/api/runs/{created['run_id']}/baseline-intake",
        json={"strategy": "none"},
    )
    assert response.status_code == 409


def test_manual_baseline_validation_422() -> None:
    created = client.post(
        "/api/runs",
        json={"domain": "seismic_event_classification", "question": "q"},
    ).json()
    response = client.post(
        f"/api/runs/{created['run_id']}/baseline-intake",
        json={"strategy": "manual_upload"},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run failing API tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_baseline_intake_api.py -q
```

Expected: FAIL with 404 for missing endpoint.

- [ ] **Step 3: Add route import**

Modify `backend/app/api/routes_runs.py` imports:

```python
from app.schemas.baseline_intake import BaselineIntakeRequest
```

- [ ] **Step 4: Add attach endpoint**

Add below `attach_experiment_assistance`:

```python
@router.post("/{run_id}/baseline-intake", response_model=ResearchRun)
async def attach_baseline_intake(run_id: str, payload: BaselineIntakeRequest) -> ResearchRun:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status != RunStatus.created:
        raise HTTPException(status_code=409, detail="baseline intake can only be attached before start")
    run.baseline_strategy = payload.strategy
    run.manual_baseline = payload
    _write_workspace(run)
    return run_store.save(run)
```

- [ ] **Step 5: Extend v3 summary**

In `get_v3_summary`, include:

```python
        "baseline_strategy": run.baseline_strategy,
        "baseline_intake": run.baseline_intake.model_dump(mode="json") if run.baseline_intake else None,
```

- [ ] **Step 6: Run API tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_baseline_intake_api.py -q
```

Expected: PASS.

---

### Task 3: Baseline Intake Agent and Gate Behavior

**Files:**
- Create: `backend/app/agents/baseline_intake_agent.py`
- Modify: `backend/app/workflows/scientist_workflow.py`
- Test: `backend/tests/test_baseline_intake_agent.py`

- [ ] **Step 1: Write failing agent tests**

Create `backend/tests/test_baseline_intake_agent.py`:

```python
import pytest

from app.agents.baseline_intake_agent import BaselineIntakeAgent
from app.schemas.baseline_intake import BaselineIntakeRequest, ManualBaselineInput, MetricObservation
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow
from app.config import Settings


@pytest.mark.asyncio
async def test_agent_normalizes_manual_baseline() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="manual_upload",
        manual_baseline=BaselineIntakeRequest(
            strategy="manual_upload",
            manual=ManualBaselineInput(
                name="User baseline",
                description="Manual baseline.",
                metrics=[MetricObservation(name="accuracy", value=0.82)],
            ),
        ),
    )
    intake = await BaselineIntakeAgent().arun(run)
    assert intake.source_type == "manual_upload"
    assert intake.trust_level == "user_provided"
    assert intake.metrics[0].value == 0.82


@pytest.mark.asyncio
async def test_agent_creates_ai_generated_demo_baseline() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="ai_generated",
    )
    intake = await BaselineIntakeAgent().arun(run)
    assert intake.source_type == "ai_generated"
    assert intake.trust_level == "runnable_demo"
    assert "not an externally verified" in " ".join(intake.limitations).lower()


@pytest.mark.asyncio
async def test_agent_marks_no_baseline_as_insufficient() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="none",
    )
    intake = await BaselineIntakeAgent().arun(run)
    assert intake.source_type == "unavailable"
    assert intake.trust_level == "insufficient"


@pytest.mark.asyncio
async def test_baseline_gate_prefers_intake() -> None:
    workflow = ScientistWorkflow(Settings())
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="ai_generated",
    )
    run.baseline_intake = await BaselineIntakeAgent().arun(run)
    await workflow._evaluate_baseline_gate(run)
    assert run.baseline_gate_status.run_gate_passed is True
    assert run.baseline_gate_status.research_gate_passed is False
    assert run.baseline_gate_status.comparison_grade == "degraded"
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_baseline_intake_agent.py -q
```

Expected: FAIL because `BaselineIntakeAgent` does not exist.

- [ ] **Step 3: Implement baseline intake agent**

Create `backend/app/agents/baseline_intake_agent.py`:

```python
from app.schemas.baseline_intake import BaselineIntake
from app.schemas.run import ResearchRun


class BaselineIntakeAgent:
    async def arun(self, run: ResearchRun) -> BaselineIntake:
        strategy = run.baseline_strategy or "none"
        if strategy == "manual_upload" and run.manual_baseline and run.manual_baseline.manual:
            manual = run.manual_baseline.manual
            return BaselineIntake(
                strategy="manual_upload",
                source_type="manual_upload",
                trust_level="user_provided",
                name=manual.name,
                description=manual.description or "User-provided baseline.",
                metrics=manual.metrics,
                limitations=[
                    "Manual baseline content was recorded but arbitrary user code was not executed by TrustSci-Agent.",
                    "Research-grade trust depends on user-supplied provenance and independent reproducibility evidence.",
                ],
                provenance_notes=[
                    "Baseline was attached before workflow start.",
                    f"repository_url={manual.repository_url or 'not supplied'}",
                    f"run_command={manual.run_command or 'not supplied'}",
                ],
            )
        if strategy == "ai_generated":
            return BaselineIntake(
                strategy="ai_generated",
                source_type="ai_generated",
                trust_level="runnable_demo",
                name="AI-generated local demo baseline",
                description=(
                    "A simple reproducible baseline represented by the fixed local seismic harness "
                    "baseline path. It is intended for demo comparison only."
                ),
                metrics=[],
                limitations=[
                    "This is not an externally verified literature SOTA baseline.",
                    "It supports local demo comparison only and should be reported as degraded research evidence.",
                ],
                provenance_notes=[
                    "Generated from the selected baseline strategy.",
                    "Executable comparison remains bounded to experiments/seismic_event_classification/train.py.",
                ],
            )
        return BaselineIntake(
            strategy="none",
            source_type="unavailable",
            trust_level="insufficient",
            name="No baseline provided",
            description="The run proceeded without a supplied or generated baseline.",
            metrics=[],
            limitations=[
                "No baseline comparison is available.",
                "Report conclusions must avoid comparative performance claims.",
            ],
            provenance_notes=["No baseline strategy payload was supplied, or the user selected no baseline."],
        )
```

- [ ] **Step 4: Wire agent into workflow**

Modify `backend/app/workflows/scientist_workflow.py` imports:

```python
from app.agents.baseline_intake_agent import BaselineIntakeAgent
```

In `ScientistWorkflow.__init__`, add:

```python
        self.baseline_intake_agent = BaselineIntakeAgent()
```

Add method near baseline methods:

```python
    async def _run_baseline_intake(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped baseline intake (non-seismic)."
            return
        run.baseline_intake = await self.baseline_intake_agent.arun(run)
        if run.steps:
            run.steps[-1].summary = (
                f"Baseline intake: {run.baseline_intake.source_type} "
                f"({run.baseline_intake.trust_level})."
            )
```

- [ ] **Step 5: Update baseline gate**

At the top of `_evaluate_baseline_gate`, after the non-seismic check, add:

```python
        if run.baseline_intake is not None:
            from app.schemas.feedback_loop import BaselineGateStatus

            intake = run.baseline_intake
            if intake.source_type == "manual_upload":
                run.baseline_gate_status = BaselineGateStatus(
                    external_verified_model_baselines=0,
                    comparable_count=1 if intake.metrics or intake.provenance_notes else 0,
                    run_gate_passed=bool(intake.metrics or intake.provenance_notes),
                    research_gate_passed=False,
                    insufficient_reasons=intake.limitations,
                    comparison_grade="degraded",
                )
            elif intake.source_type == "ai_generated":
                run.baseline_gate_status = BaselineGateStatus(
                    external_verified_model_baselines=0,
                    comparable_count=1,
                    run_gate_passed=True,
                    research_gate_passed=False,
                    insufficient_reasons=intake.limitations,
                    comparison_grade="degraded",
                )
            else:
                run.baseline_gate_status = BaselineGateStatus(
                    external_verified_model_baselines=0,
                    comparable_count=0,
                    run_gate_passed=False,
                    research_gate_passed=False,
                    insufficient_reasons=intake.limitations,
                    comparison_grade="degraded",
                )
            if run.steps:
                g = run.baseline_gate_status
                run.steps[-1].summary = (
                    f"Baseline gate from intake: {g.comparison_grade} "
                    f"(run_gate={g.run_gate_passed}, research_gate={g.research_gate_passed})."
                )
            return
```

- [ ] **Step 6: Run agent tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_baseline_intake_agent.py -q
```

Expected: PASS.

---

### Task 4: Workflow Routing Removes Automatic Baseline Mining

**Files:**
- Modify: `backend/app/workflows/scientist_workflow.py`
- Modify: `backend/app/workflows/langgraph_workflow.py`
- Test: update `backend/tests/test_s4_langgraph.py`, `backend/tests/test_s5_langgraph_cycles.py`, `backend/tests/test_workflow_classic_s5.py`

- [ ] **Step 1: Update expected workflow tests first**

In workflow tests that currently list `_extract_code_urls`, `_discover_baselines_auto`, and `_verify_baselines_auto` as main seismic stubs, replace those expected stubs with `_run_baseline_intake`.

Example assertion pattern:

```python
assert "baseline_intake" in names
assert "baseline_discover" not in names
assert "baseline_verify" not in names
assert names.index("baseline_intake") > names.index("novelty_check")
assert names.index("baseline_quality_gate") > names.index("baseline_intake")
```

For LangGraph tests, update the completed node list to include:

```python
"baseline_intake",
"baseline_quality_gate",
"experiment_design",
```

and not include:

```python
"extract_code_urls",
"baseline_discover",
"baseline_verify",
```

- [ ] **Step 2: Run focused workflow tests to see failures**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s4_langgraph.py backend/tests/test_s5_langgraph_cycles.py backend/tests/test_workflow_classic_s5.py -q
```

Expected: FAIL because implementation still emits old baseline nodes.

- [ ] **Step 3: Change classic workflow path**

In `ScientistWorkflow._run_after_evidence_review`, replace:

```python
            await self._step(run, "extract_code_urls", self._extract_code_urls)
            await self._step(run, "baseline_discover", self._discover_baselines_auto)
            await self._step(run, "baseline_verify", self._verify_baselines_auto)
            await self._step(run, "baseline_quality_gate", self._evaluate_baseline_gate)
```

with:

```python
            await self._step(run, "baseline_intake", self._run_baseline_intake)
            await self._step(run, "baseline_quality_gate", self._evaluate_baseline_gate)
```

Leave `_extract_code_urls`, `_discover_baselines_auto`, and `_verify_baselines_auto` methods in the file for compatibility with legacy/manual endpoints.

- [ ] **Step 4: Change LangGraph nodes and edges**

In `backend/app/workflows/langgraph_workflow.py`, remove these main path node additions and edges:

```python
        graph.add_node("extract_code_urls", self._make_step_node("extract_code_urls", "_extract_code_urls"))
        graph.add_node("baseline_discover", self._make_step_node("baseline_discover", "_discover_baselines_auto"))
        graph.add_node("baseline_verify", self._make_step_node("baseline_verify", "_verify_baselines_auto"))
        graph.add_edge("extract_code_urls", "baseline_discover")
        graph.add_edge("baseline_discover", "baseline_verify")
        graph.add_edge("baseline_verify", "baseline_quality_gate")
```

Add:

```python
        graph.add_node("baseline_intake", self._make_step_node("baseline_intake", "_run_baseline_intake"))
        graph.add_edge("baseline_intake", "baseline_quality_gate")
```

Change novelty route mapping from:

```python
{"arena": "arena", "extract_code_urls": "extract_code_urls"}
```

to:

```python
{"arena": "arena", "baseline_intake": "baseline_intake"}
```

Update `_route_after_novelty` return values:

```python
    def _route_after_novelty(self, state) -> str:
        run = state["run"]
        if run.domain != "seismic_event_classification":
            return "baseline_intake"
        v = run.novelty_verdict
        if v and v.verdict == "already_done" and run.novelty_round < 2:
            return "arena"
        return "baseline_intake"
```

Change `_route_after_research` so stale S5 re-search loops do not re-enter removed baseline discovery:

```python
    def _route_after_research(self, state) -> str:
        run = state["run"]
        return "evidence_ledger" if run.evidence_changed else "baseline_intake"
```

Update conditional edge mapping after `re_search_literature`:

```python
{"evidence_ledger": "evidence_ledger", "baseline_intake": "baseline_intake"}
```

- [ ] **Step 5: Update step descriptions**

In `_stage_summary` or the stage summary dict near the bottom of `scientist_workflow.py`, add:

```python
"baseline_intake": "Recording user-selected baseline strategy and provenance.",
```

Optionally leave old descriptions for legacy methods.

- [ ] **Step 6: Run focused workflow tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s4_langgraph.py backend/tests/test_s5_langgraph_cycles.py backend/tests/test_workflow_classic_s5.py -q
```

Expected: PASS after test expectations are updated.

---

### Task 5: Experiment Redesign Schemas, Agent, and Result Gate

**Files:**
- Modify: `backend/app/schemas/run.py`
- Create: `backend/app/agents/experiment_redesign_agent.py`
- Modify: `backend/app/workflows/scientist_workflow.py`
- Test: `backend/tests/test_experiment_redesign.py`, update `backend/tests/test_macro_react.py`

- [ ] **Step 1: Write failing redesign tests**

Create `backend/tests/test_experiment_redesign.py`:

```python
import pytest

from app.agents.experiment_redesign_agent import ExperimentRedesignAgent
from app.config import Settings
from app.schemas.code_experiment import CodeExperimentResult, ComparisonResult, ExperimentSummary
from app.schemas.experiment import ExperimentPlan
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


def _run_with_negative_result() -> ResearchRun:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        experiment_plan=ExperimentPlan(
            datasets=["synthetic seismic demo"],
            source="waveform",
            target="event_class",
            baselines=["harness baseline"],
            metrics=["accuracy"],
            experiment_steps=["train initial model"],
            expected_results="Beat baseline.",
            failure_modes=["overfitting"],
        ),
    )
    run.code_experiment = CodeExperimentResult(
        comparison=ComparisonResult(
            baseline_metrics={"accuracy": 0.90},
            method_metrics={"accuracy": 0.70},
            method_beats_baseline=False,
            outcome="completed_negative",
            notes=["method underperformed"],
        ),
        summary=ExperimentSummary(
            outcome="completed_negative",
            tests_pass=True,
            method_beats_baseline=False,
            best_metric=0.70,
        ),
    )
    return run


@pytest.mark.asyncio
async def test_redesign_agent_adds_rationale_and_new_step() -> None:
    run = _run_with_negative_result()
    plan = await ExperimentRedesignAgent().arun(run)
    assert "Redesign rationale" in plan.experiment_steps[0]
    assert plan.expected_results
    assert len(plan.experiment_steps) >= len(run.experiment_plan.experiment_steps)


@pytest.mark.asyncio
async def test_result_gate_routes_completed_negative_to_redesign() -> None:
    workflow = ScientistWorkflow(Settings())
    run = _run_with_negative_result()
    route = workflow._route_after_experiment_result({"run": run})
    assert route == "experiment_redesign"


@pytest.mark.asyncio
async def test_redesign_cap_routes_to_result_evaluation() -> None:
    workflow = ScientistWorkflow(Settings())
    run = _run_with_negative_result()
    run.experiment_redesign_round = 1
    route = workflow._route_after_experiment_result({"run": run})
    assert route == "result_evaluation"


@pytest.mark.asyncio
async def test_experiment_redesign_updates_plan_and_counter() -> None:
    workflow = ScientistWorkflow(Settings())
    run = _run_with_negative_result()
    await workflow._redesign_experiment(run)
    assert run.experiment_redesign_round == 1
    assert "Redesign rationale" in run.experiment_plan.experiment_steps[0]
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_experiment_redesign.py -q
```

Expected: FAIL because `ExperimentRedesignAgent` and run field do not exist.

- [ ] **Step 3: Add redesign state field**

Modify `backend/app/schemas/run.py` near S5 loop state:

```python
    experiment_redesign_round: int = 0
```

- [ ] **Step 4: Implement redesign agent**

Create `backend/app/agents/experiment_redesign_agent.py`:

```python
from copy import deepcopy

from app.schemas.experiment import ExperimentPlan
from app.schemas.run import ResearchRun


class ExperimentRedesignAgent:
    async def arun(self, run: ResearchRun) -> ExperimentPlan:
        base = deepcopy(run.experiment_plan)
        if base is None:
            return ExperimentPlan(
                datasets=["synthetic seismic demo"],
                source="waveform",
                target="event_class",
                baselines=["selected baseline strategy"],
                metrics=["accuracy", "macro_f1"],
                experiment_steps=[
                    "Redesign rationale: previous experiment plan was missing, so use a conservative waveform baseline comparison.",
                    "Extract time-domain and spectral summary features before model training.",
                    "Evaluate on the fixed event-level test split and compare against the harness baseline.",
                ],
                expected_results="The redesigned experiment should expose whether feature changes improve robustness.",
                failure_modes=["No improvement after redesign", "Synthetic split is too easy or too small"],
            )
        notes = []
        if run.code_experiment and run.code_experiment.comparison.notes:
            notes = run.code_experiment.comparison.notes
        rationale = "Redesign rationale: previous executable result underperformed the selected baseline."
        if notes:
            rationale += f" Last comparison note: {notes[0]}"
        base.experiment_steps = [
            rationale,
            "Add or emphasize spectral and time-domain feature checks before fitting the classifier.",
            "Re-run the same fixed split so the redesigned result remains comparable.",
        ] + list(base.experiment_steps)
        if "macro_f1" not in base.metrics:
            base.metrics.append("macro_f1")
        base.expected_results = (
            "The redesigned experiment should recover performance or provide a clearer negative result "
            "with documented limitations."
        )
        if "Redesign still fails to beat baseline" not in base.failure_modes:
            base.failure_modes.append("Redesign still fails to beat baseline")
        return base
```

- [ ] **Step 5: Wire agent into workflow**

Modify imports in `scientist_workflow.py`:

```python
from app.agents.experiment_redesign_agent import ExperimentRedesignAgent
```

In `__init__`, add:

```python
        self.experiment_redesigner = ExperimentRedesignAgent()
```

Add methods:

```python
    async def _evaluate_experiment_result_gate(self, run: ResearchRun) -> None:
        ce = run.code_experiment
        if ce is None:
            if run.steps:
                run.steps[-1].summary = "Experiment result gate: no code experiment result."
            return
        if run.steps:
            run.steps[-1].summary = (
                f"Experiment result gate: {ce.summary.outcome}, "
                f"redesign_round={run.experiment_redesign_round}."
            )

    def _route_after_experiment_result(self, state) -> str:
        run = state["run"] if isinstance(state, dict) else state
        ce = run.code_experiment
        if run.domain != "seismic_event_classification" or ce is None:
            return "result_evaluation"
        if run.experiment_redesign_round >= 1:
            return "result_evaluation"
        if ce.summary.outcome == "completed_negative":
            baseline = _baseline_metric(ce.comparison)
            method = ce.summary.best_metric
            margin = (baseline - method) if baseline is not None and method is not None else None
            if margin is None or margin >= 0.05:
                return "experiment_redesign"
        return "result_evaluation"

    async def _redesign_experiment(self, run: ResearchRun) -> None:
        if run.domain != "seismic_event_classification":
            if run.steps:
                run.steps[-1].summary = "Skipped experiment redesign (non-seismic)."
            return
        run.experiment_plan = await self.experiment_redesigner.arun(run)
        run.experiment_redesign_round += 1
        run.code_experiment_mode = "redesign"
        if run.steps:
            run.steps[-1].summary = f"Redesigned experiment plan (round {run.experiment_redesign_round})."
```

- [ ] **Step 6: Allow code writer trigger value**

In `_run_code_experiment`, treat `code_experiment_mode == "redesign"` like an initial generation with the redesigned experiment plan:

```python
            elif mode == "redesign":
                source = await self.code_writer.arun(
                    "initial", selected, run.experiment_plan, run_id=run.run_id)
                trigger = "redesign"
```

Place this branch before the final `else`.

- [ ] **Step 7: Update classic workflow path**

In `ScientistWorkflow._run_after_evidence_review`, after `code_experiment`, replace direct `macro_react` flow with:

```python
            await self._step(run, "experiment_result_gate", self._evaluate_experiment_result_gate)
            if self._route_after_experiment_result({"run": run}) == "experiment_redesign":
                await self._step(run, "experiment_redesign", self._redesign_experiment)
                await self._step(run, "code_experiment", self._run_code_experiment)
                await self._step(run, "experiment_result_gate", self._evaluate_experiment_result_gate)
```

Leave `_run_macro_react` in place for compatibility, but it should no longer be the default completed-negative path.

- [ ] **Step 8: Run redesign tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_experiment_redesign.py backend/tests/test_macro_react.py -q
```

Expected: PASS, with `test_macro_react.py` updated only if assertions conflict with the new demoted role.

---

### Task 6: LangGraph Experiment Redesign Routing

**Files:**
- Modify: `backend/app/workflows/langgraph_workflow.py`
- Test: update `backend/tests/test_s5_langgraph_cycles.py`, `backend/tests/test_langgraph_workflow.py`

- [ ] **Step 1: Write/update LangGraph route test**

Add or update a test in `backend/tests/test_s5_langgraph_cycles.py`:

```python
@pytest.mark.asyncio
async def test_completed_negative_routes_to_experiment_redesign(monkeypatch):
    from app.schemas.code_experiment import CodeExperimentResult, ComparisonResult, ExperimentSummary

    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(max_papers=1),
    )
    workflow = LangGraphWorkflow(Settings(workflow_engine="langgraph"))

    async def fake_code(run):
        run.code_experiment = CodeExperimentResult(
            comparison=ComparisonResult(
                baseline_metrics={"accuracy": 0.9},
                method_metrics={"accuracy": 0.7},
                method_beats_baseline=False,
                outcome="completed_negative",
            ),
            summary=ExperimentSummary(
                outcome="completed_negative",
                tests_pass=True,
                method_beats_baseline=False,
                best_metric=0.7,
            ),
        )

    monkeypatch.setattr(workflow, "_run_code_experiment", fake_code)
    result = await workflow.run(run)
    names = [step.name for step in result.steps]
    assert "experiment_redesign" in names
    assert names.count("code_experiment") >= 2
```

If existing harness fixtures stub methods differently, adapt the monkeypatch to that fixture style while keeping the same assertions.

- [ ] **Step 2: Run failing LangGraph tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s5_langgraph_cycles.py backend/tests/test_langgraph_workflow.py -q
```

Expected: FAIL until graph edges exist.

- [ ] **Step 3: Add graph nodes and routing**

In `backend/app/workflows/langgraph_workflow.py`, after `code_experiment`, replace the `macro_react` conditional edge as the main path.

Add:

```python
        graph.add_node("experiment_result_gate", self._make_step_node("experiment_result_gate", "_evaluate_experiment_result_gate"))
        graph.add_node("experiment_redesign", self._make_step_node("experiment_redesign", "_redesign_experiment"))
        graph.add_edge("code_experiment", "experiment_result_gate")
        graph.add_conditional_edges(
            "experiment_result_gate",
            self._route_after_experiment_result,
            {"experiment_redesign": "experiment_redesign", "result_evaluation": "result_evaluation"},
        )
        graph.add_edge("experiment_redesign", "code_experiment")
```

Remove or bypass the main-path edge:

```python
graph.add_edge("code_experiment", "macro_react")
```

and its main conditional route to report. Keep `macro_react` method available but not used by the normal completed-negative route.

- [ ] **Step 4: Ensure mapping names match exactly**

Verify `_route_after_experiment_result` returns only:

```python
"experiment_redesign"
"result_evaluation"
```

and the conditional edge mapping uses exactly those keys.

- [ ] **Step 5: Run focused LangGraph tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s5_langgraph_cycles.py backend/tests/test_langgraph_workflow.py -q
```

Expected: PASS.

---

### Task 7: Report Provenance and Summary Updates

**Files:**
- Modify: `backend/app/agents/report_writer_agent.py`
- Modify: `backend/app/api/routes_runs.py`
- Test: update `backend/tests/test_s6_report_provenance.py`, add assertions in `backend/tests/test_baseline_intake_api.py`

- [ ] **Step 1: Write failing provenance test**

Update `backend/tests/test_s6_report_provenance.py` or add a new test:

```python
from app.agents.report_writer_agent import _system_provenance
from app.schemas.baseline_intake import BaselineIntake, MetricObservation
from app.schemas.run import ResearchConstraints, ResearchRun


def test_report_provenance_prefers_baseline_intake() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="manual_upload",
        baseline_intake=BaselineIntake(
            strategy="manual_upload",
            source_type="manual_upload",
            trust_level="user_provided",
            name="User baseline",
            description="Manual baseline.",
            metrics=[MetricObservation(name="accuracy", value=0.8)],
            limitations=["manual limitation"],
            provenance_notes=["attached before start"],
        ),
    )
    provenance = _system_provenance(run, [], [], [])
    assert provenance.baseline_provenance["source_type"] == "manual_upload"
    assert provenance.baseline_provenance["trust_level"] == "user_provided"
    assert provenance.baseline_provenance["limitations"] == ["manual limitation"]
```

- [ ] **Step 2: Run failing provenance test**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_report_provenance.py -q
```

Expected: FAIL because provenance still uses old experiment assistance/code experiment branches first.

- [ ] **Step 3: Update provenance baseline block**

In `backend/app/agents/report_writer_agent.py`, replace `baseline_provenance=(...)` expression inside `_system_provenance` with a helper call:

```python
        baseline_provenance=_baseline_provenance(run),
```

Add helper near `_system_provenance`:

```python
def _baseline_provenance(run: ResearchRun) -> dict[str, Any]:
    if run.baseline_intake:
        return {
            "strategy": run.baseline_intake.strategy,
            "source_type": run.baseline_intake.source_type,
            "trust_level": run.baseline_intake.trust_level,
            "name": run.baseline_intake.name,
            "description": run.baseline_intake.description,
            "metrics": [item.model_dump(mode="json") for item in run.baseline_intake.metrics],
            "limitations": run.baseline_intake.limitations,
            "provenance_notes": run.baseline_intake.provenance_notes,
        }
    if run.experiment_assistance:
        return {
            "source": "user-provided",
            "name": run.experiment_assistance.baseline_name,
            "metrics": [item.model_dump(mode="json") for item in run.experiment_assistance.baseline_metrics],
        }
    if run.code_experiment:
        return {
            "source": "system-executed",
            "baseline": run.code_experiment.baseline_source,
            "comparison": run.code_experiment.comparison.model_dump(mode="json"),
        }
    return {}
```

- [ ] **Step 4: Extend v3 summary warnings**

In `routes_runs.py`, after baseline gate warnings, include baseline intake limitations:

```python
    if run.baseline_intake:
        warnings.extend(run.baseline_intake.limitations)
```

Add summary keys if not already added in Task 2:

```python
        "baseline_strategy": run.baseline_strategy,
        "baseline_intake": run.baseline_intake.model_dump(mode="json") if run.baseline_intake else None,
        "experiment_redesign_round": run.experiment_redesign_round,
```

- [ ] **Step 5: Run provenance/API tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_s6_report_provenance.py backend/tests/test_baseline_intake_api.py -q
```

Expected: PASS.

---

### Task 8: Frontend API Types and Baseline Intake Start Flow

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/workbench/Workbench.tsx`
- Test: TypeScript build after component tasks

- [ ] **Step 1: Add TypeScript types**

In `frontend/lib/api.ts`, add near experiment assistance types:

```ts
export type BaselineStrategy = "manual_upload" | "ai_generated" | "none";

export type BaselineMetricObservation = {
  name: string;
  value: number;
  unit?: string | null;
  split?: string | null;
  notes?: string | null;
};

export type ManualBaselineInput = {
  name: string;
  description: string;
  code_text?: string | null;
  repository_url?: string | null;
  run_command?: string | null;
  dataset_description: string;
  metrics: BaselineMetricObservation[];
  notes: string;
};

export type BaselineIntakeRequest = {
  strategy: BaselineStrategy;
  manual?: ManualBaselineInput | null;
};

export type BaselineIntake = {
  strategy: BaselineStrategy;
  source_type: "manual_upload" | "ai_generated" | "unavailable";
  trust_level: "user_provided" | "runnable_demo" | "insufficient";
  name: string;
  description: string;
  metrics: BaselineMetricObservation[];
  limitations: string[];
  provenance_notes: string[];
};
```

Extend `ResearchRun`:

```ts
  baseline_strategy?: BaselineStrategy;
  manual_baseline?: BaselineIntakeRequest | null;
  baseline_intake?: BaselineIntake | null;
  experiment_redesign_round?: number;
```

- [ ] **Step 2: Add API function**

In `frontend/lib/api.ts`:

```ts
export async function attachBaselineIntake(runId: string, payload: BaselineIntakeRequest) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/baseline-intake`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
```

- [ ] **Step 3: Add baseline draft state**

In `Workbench.tsx` imports, include:

```ts
  attachBaselineIntake,
  BaselineIntakeRequest,
```

Extend `ConsoleDraft`:

```ts
  baselineIntake: BaselineIntakeRequest;
```

Add default:

```ts
const defaultBaselineIntake: BaselineIntakeRequest = {
  strategy: "ai_generated"
};
```

Add `baselineIntake: {...defaultBaselineIntake}` to both draft defaults, or use `none` for classic and `ai_generated` for seismic:

```ts
baselineIntake: { strategy: "none" }
```

for classic and:

```ts
baselineIntake: { strategy: "ai_generated" }
```

for seismic.

- [ ] **Step 4: Attach baseline before start**

In `handleStart`, after `createRun(...)` and before experiment assistance/start, add:

```ts
      const withBaseline = runDomain === "seismic_event_classification"
        ? await attachBaselineIntake(created.run_id, draft.baselineIntake)
        : created;
      const ready = draft.researchMode === "experiment_assistance"
        ? await attachExperimentAssistance(withBaseline.run_id, draft.experimentAssistance) : withBaseline;
```

Remove or replace the older `const ready = ... created ...` line.

- [ ] **Step 5: Defer build until UI component task**

Do not run frontend build yet if `BaselineIntakePanel` imports are not added. Build after Task 10.

---

### Task 9: Frontend Baseline Intake UI and Baseline Board

**Files:**
- Create: `frontend/components/workbench/BaselineIntakePanel.tsx`
- Modify: `frontend/components/workbench/BaselineBoard.tsx`
- Modify: `frontend/components/workbench/Workbench.tsx`

- [ ] **Step 1: Create BaselineIntakePanel**

Create `frontend/components/workbench/BaselineIntakePanel.tsx`:

```tsx
import { BaselineIntakeRequest, BaselineStrategy } from "../../lib/api";

type Props = {
  value: BaselineIntakeRequest;
  onChange: (value: BaselineIntakeRequest) => void;
};

const emptyManual = {
  name: "",
  description: "",
  code_text: "",
  repository_url: "",
  run_command: "",
  dataset_description: "",
  metrics: [{ name: "accuracy", value: 0, split: "test" }],
  notes: ""
};

export function BaselineIntakePanel({ value, onChange }: Props) {
  const manual = value.manual || emptyManual;

  function setStrategy(strategy: BaselineStrategy) {
    if (strategy === "manual_upload") {
      onChange({ strategy, manual });
    } else {
      onChange({ strategy });
    }
  }

  function updateManual<K extends keyof typeof emptyManual>(key: K, next: (typeof emptyManual)[K]) {
    onChange({ strategy: "manual_upload", manual: { ...manual, [key]: next } });
  }

  function updateMetric(index: number, key: "name" | "value" | "split", next: string | number) {
    const metrics = [...(manual.metrics || [])];
    metrics[index] = { ...metrics[index], [key]: key === "value" ? Number(next) : String(next) };
    updateManual("metrics", metrics);
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Baseline 来源</h2>
        <span className="badge">{strategyLabel(value.strategy)}</span>
      </div>
      <div className="segmented">
        <button type="button" className={value.strategy === "manual_upload" ? "active" : ""} onClick={() => setStrategy("manual_upload")}>人工上传</button>
        <button type="button" className={value.strategy === "ai_generated" ? "active" : ""} onClick={() => setStrategy("ai_generated")}>AI 生成 demo</button>
        <button type="button" className={value.strategy === "none" ? "active" : ""} onClick={() => setStrategy("none")}>暂不提供</button>
      </div>
      {value.strategy === "manual_upload" && (
        <div className="form-grid">
          <label>名称<input value={manual.name} onChange={(e) => updateManual("name", e.target.value)} /></label>
          <label>仓库链接<input value={manual.repository_url || ""} onChange={(e) => updateManual("repository_url", e.target.value)} /></label>
          <label>运行命令<input value={manual.run_command || ""} onChange={(e) => updateManual("run_command", e.target.value)} /></label>
          <label>数据集说明<textarea value={manual.dataset_description} onChange={(e) => updateManual("dataset_description", e.target.value)} /></label>
          <label>方法说明<textarea value={manual.description} onChange={(e) => updateManual("description", e.target.value)} /></label>
          <label>代码文本<textarea value={manual.code_text || ""} onChange={(e) => updateManual("code_text", e.target.value)} /></label>
          <label>备注<textarea value={manual.notes} onChange={(e) => updateManual("notes", e.target.value)} /></label>
          <div className="metric-row">
            {(manual.metrics || []).map((metric, index) => (
              <span className="metric-editor" key={index}>
                <input value={metric.name} onChange={(e) => updateMetric(index, "name", e.target.value)} />
                <input type="number" value={metric.value} onChange={(e) => updateMetric(index, "value", e.target.value)} />
                <input value={metric.split || ""} onChange={(e) => updateMetric(index, "split", e.target.value)} />
              </span>
            ))}
          </div>
        </div>
      )}
      {value.strategy === "ai_generated" && <p className="muted">系统将创建一个简单可复现的 demo baseline；它不是外部验证的 SOTA baseline。</p>}
      {value.strategy === "none" && <p className="muted">报告会把 baseline 对比标记为不可用或降级，不生成强对比结论。</p>}
    </section>
  );
}

function strategyLabel(strategy: BaselineStrategy) {
  if (strategy === "manual_upload") return "人工上传";
  if (strategy === "ai_generated") return "AI 生成";
  return "无 baseline";
}
```

- [ ] **Step 2: Render panel in seismic draft**

In `Workbench.tsx`, import:

```ts
import { BaselineIntakePanel } from "./BaselineIntakePanel";
```

Near existing seismic draft panels, render:

```tsx
{activeVersion === "seismic" && (
  <BaselineIntakePanel
    value={draft.baselineIntake}
    onChange={(value) => updateDraft("baselineIntake", value)}
  />
)}
```

- [ ] **Step 3: Update BaselineBoard primary display**

At the top of `BaselineBoard`, derive:

```tsx
const intake = run?.baseline_intake;
```

Render before candidate list:

```tsx
{intake && (
  <article className="item">
    <div className="item-title">{intake.name || "Baseline intake"}</div>
    <div className="item-meta">
      来源 {sourceLabel(intake.source_type)} · 可信级别 {trustLabel(intake.trust_level)}
    </div>
    <p className="muted">{intake.description}</p>
    <div className="metric-row">
      {intake.metrics.map((metric) => (
        <span className="badge" key={`${metric.name}-${metric.split || "all"}`}>
          {metric.name}: {metric.value}{metric.unit ? ` ${metric.unit}` : ""}
        </span>
      ))}
      {!intake.metrics.length && <span className="badge warn">无可比指标</span>}
    </div>
    {intake.limitations.map((item, index) => <p className="muted" key={index}>限制：{item}</p>)}
  </article>
)}
```

Add helpers:

```tsx
function sourceLabel(source: string) {
  if (source === "manual_upload") return "人工上传";
  if (source === "ai_generated") return "AI 生成 demo";
  return "未提供";
}

function trustLabel(level: string) {
  if (level === "user_provided") return "用户提供";
  if (level === "runnable_demo") return "demo 可运行";
  return "不足";
}
```

Keep old candidate list but label it as legacy if displayed:

```tsx
<h3>Legacy 自动发现候选（已从主流程移除）</h3>
```

- [ ] **Step 4: Run frontend type check via build after Task 10**

Build after PaperReader is wired so missing imports are found together.

---

### Task 10: Lightweight Paper Reader

**Files:**
- Modify: `frontend/components/workbench/LiteratureBoard.tsx`
- Create: `frontend/components/workbench/PaperReaderPanel.tsx`
- Modify: `frontend/components/workbench/Workbench.tsx`

- [ ] **Step 1: Update LiteratureBoard props**

Change signature:

```tsx
export function LiteratureBoard({
  run,
  selectedPaperId,
  onSelectPaper
}: {
  run: ResearchRun | null;
  selectedPaperId?: string | null;
  onSelectPaper?: (paperId: string) => void;
}) {
```

Change article class and click:

```tsx
<article
  className={`item ${selectedPaperId === paper.paper_id ? "active" : ""}`}
  key={paper.paper_id}
  onClick={() => onSelectPaper?.(paper.paper_id)}
>
```

Prevent link clicks from triggering selection if needed:

```tsx
onClick={(event) => event.stopPropagation()}
```

on source/PDF anchors.

- [ ] **Step 2: Create PaperReaderPanel**

Create `frontend/components/workbench/PaperReaderPanel.tsx`:

```tsx
import { ExternalLink, FileText } from "lucide-react";
import { ResearchRun } from "../../lib/api";

type Paper = ResearchRun["papers"][number];

export function PaperReaderPanel({ paper }: { paper: Paper | null }) {
  if (!paper) {
    return (
      <section className="panel span-4">
        <div className="panel-heading"><h2><FileText size={16} /> 文献原文</h2></div>
        <p className="muted">点击左侧文献后，这里会显示摘要、来源链接和 PDF 预览。</p>
      </section>
    );
  }

  return (
    <section className="panel span-4 paper-reader">
      <div className="panel-heading">
        <h2><FileText size={16} /> 文献原文</h2>
        <span className="badge">{paper.source_api || "unknown"}</span>
      </div>
      <div className="item-title">{paper.title}</div>
      <div className="item-meta">
        {paper.year || paper.publication_date || "未知年份"}
        {paper.venue ? ` · ${paper.venue}` : ""}
        {paper.authors?.length ? ` · ${paper.authors.slice(0, 3).join(", ")}` : ""}
      </div>
      <div className="item-meta">
        DOI {paper.doi || "无"}
        {paper.arxiv_id ? ` · arXiv ${paper.arxiv_id}` : ""}
      </div>
      {paper.abstract ? <p className="muted">{paper.abstract}</p> : <p className="muted">暂无摘要。</p>}
      <div className="item-actions">
        {paper.source_url && (
          <a className="secondary link-button" href={paper.source_url} target="_blank" rel="noreferrer">
            <ExternalLink size={14} /> 外部来源
          </a>
        )}
        {paper.pdf_url && (
          <a className="secondary link-button" href={paper.pdf_url} target="_blank" rel="noreferrer">
            <FileText size={14} /> 打开 PDF
          </a>
        )}
      </div>
      {paper.pdf_url ? (
        <iframe className="paper-frame" src={paper.pdf_url} title={paper.title} />
      ) : (
        <p className="muted">该记录没有 PDF 链接。后续增强版可通过 browser-worker 尝试网页截图或下载预览。</p>
      )}
      <p className="muted">如果 PDF 区域为空，通常是来源网站禁止内嵌显示；请使用“打开 PDF”或“外部来源”。</p>
    </section>
  );
}
```

- [ ] **Step 3: Wire selected paper state**

In `Workbench.tsx`, import:

```ts
import { PaperReaderPanel } from "./PaperReaderPanel";
```

Add state:

```ts
const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
```

Add derived paper:

```ts
const selectedPaper = run?.papers.find((paper) => paper.paper_id === selectedPaperId) || run?.papers[0] || null;
```

When selecting a new run, reset:

```ts
setSelectedPaperId(nextRun.papers[0]?.paper_id || null);
```

Render literature board:

```tsx
<LiteratureBoard run={run} selectedPaperId={selectedPaper?.paper_id || null} onSelectPaper={setSelectedPaperId} />
<PaperReaderPanel paper={selectedPaper} />
```

Place `PaperReaderPanel` in the right-side seismic grid beside the literature list.

- [ ] **Step 4: Add minimal CSS if needed**

In `frontend/app/globals.css`, add:

```css
.paper-reader {
  min-height: 520px;
}

.paper-frame {
  width: 100%;
  min-height: 420px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
}

.item.active {
  border-color: rgba(96, 165, 250, 0.8);
}
```

- [ ] **Step 5: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: TypeScript and production build PASS.

---

### Task 11: Docs, Full Verification, and Cleanup

**Files:**
- Modify if needed: `README.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `SESSION_HANDOFF.md`
- No tests created in this task.

- [ ] **Step 1: Update docs**

Update docs to reflect:

- Baseline no longer auto-mined from papers/code links in the main workflow.
- Baseline strategies are manual upload, AI-generated demo, or none.
- Poor completed results trigger experiment redesign.
- Paper reader v1 is lightweight and does not use browser-worker.

Minimum files:

```text
README.md
docs/ARCHITECTURE.md
docs/API.md
SESSION_HANDOFF.md
```

- [ ] **Step 2: Run focused backend tests**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest backend/tests/test_baseline_intake_schemas.py backend/tests/test_baseline_intake_api.py backend/tests/test_baseline_intake_agent.py backend/tests/test_experiment_redesign.py backend/tests/test_s4_langgraph.py backend/tests/test_s5_langgraph_cycles.py backend/tests/test_s6_report_provenance.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full backend test suite**

Run:

```powershell
& backend/.venv/Scripts/python.exe -m pytest -q
```

Expected: PASS. Existing warnings are acceptable if unchanged.

- [ ] **Step 4: Run frontend production build**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 5: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors. Git may print CRLF warnings; record them if they are pre-existing or harmless.

- [ ] **Step 6: Review changed files**

Run:

```powershell
git status --short
git diff --stat
```

Expected: changed files match this plan. Do not commit.

---

## Execution Notes

- Prefer small, test-first edits.
- Do not delete legacy baseline discovery files unless tests prove they conflict with the new main route.
- Keep `experiment_assistance` analysis-only; do not execute user-submitted code.
- If Docker CLI is still unavailable in the current shell, skip Docker Compose validation and mention it in the final handoff.
- If frontend Chinese text around touched components is already mojibake, replace only the touched labels with clean UTF-8 Chinese. Do not do a whole-app copy rewrite unless the user separately asks for it.

## Self-Review Checklist

- Spec coverage: baseline strategy, API, workflow route removal, experiment redesign, paper reader, provenance, docs, and tests are all mapped to tasks.
- Placeholder scan: no `TBD` or open implementation placeholders should remain.
- Type consistency: backend names are `BaselineIntakeRequest`, `ManualBaselineInput`, `BaselineIntake`, `baseline_strategy`, `manual_baseline`, `baseline_intake`, and `experiment_redesign_round`; frontend names mirror these.
- No commits: plan intentionally omits commit steps because the user requested local-only changes in this project.
