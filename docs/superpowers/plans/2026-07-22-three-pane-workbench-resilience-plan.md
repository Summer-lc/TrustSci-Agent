# Three-Pane Research Workbench and Run Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a three-pane research workbench with direct conversational execution, visible workflow stages, one automatic retry, user-selected history recovery, controlled retry/skip actions, and cached paper-page preview fallback.

**Architecture:** Keep the existing FastAPI workflows and run model, add a small run-control layer around individual workflow steps, and expose stable action endpoints. Split the Next.js workbench into a conversation pane, stage navigator/content pane, and paper reader pane, with the existing panels reused inside stage groups. Paper preview uses the existing browser-worker and the shared `data` volume.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest, Next.js 16, React 19, TypeScript, CSS, Playwright browser-worker, Docker Compose.

**Repository constraint:** Do not create Git commits. The user's existing uncommitted work must remain intact.

---

## File Map

**Create**

- `backend/app/schemas/run_control.py` — step error/action schemas and paper-preview response.
- `backend/app/workflows/run_control.py` — error classification, retry policy, skip policy, and step history helpers.
- `backend/tests/test_run_control.py` — unit tests for error classification and step transitions.
- `backend/tests/test_run_actions_api.py` — API tests for retry, skip, and recovery.
- `backend/tests/test_paper_preview_api.py` — preview routing, cache, and artifact-serving tests.
- `frontend/components/workbench/ResearchConversation.tsx` — direct task input and structured run messages.
- `frontend/components/workbench/ResearchStageNavigator.tsx` — grouped stage navigation and loop badges.
- `frontend/components/workbench/ResearchStageContent.tsx` — renders existing panels by active stage.
- `frontend/lib/workbench.ts` — pure stage grouping, message mapping, and action visibility helpers.
- `frontend/lib/workbench.test.ts` — Vitest tests for the pure workbench helpers.

**Modify**

- `backend/app/schemas/common.py` — enrich `AgentStep` without breaking old snapshots.
- `backend/app/schemas/run.py` — recovery counter, trust warnings, and last action metadata.
- `backend/app/workflows/scientist_workflow.py` — resilient `_step`, waiting-action handling, and tail resume.
- `backend/app/workflows/langgraph_workflow.py` — preserve waiting-action state instead of collapsing it to `failed`.
- `backend/app/api/routes_runs.py` — run action and recovery endpoints.
- `backend/app/api/routes_browser.py` — cached paper preview and safe artifact response.
- `backend/app/schemas/browser.py` — browser preview types.
- `frontend/lib/api.ts` — step/action/preview types and API functions.
- `frontend/components/workbench/Workbench.tsx` — state orchestration only; compose the three panes.
- `frontend/components/workbench/PaperReaderPanel.tsx` — PDF-first and webpage-preview fallback.
- `frontend/components/workbench/RunHistory.tsx` — explicit selection/recovery metadata.
- `frontend/app/globals.css` — desktop three-pane and responsive drawer/tab layout.
- `frontend/package.json` and `frontend/package-lock.json` — add Vitest test runner.
- `docs/API.md` and `docs/ARCHITECTURE.md` — document run actions and preview fallback.

## Task 1: Add Backward-Compatible Run-Control Schemas

**Files:**

- Create: `backend/app/schemas/run_control.py`
- Modify: `backend/app/schemas/common.py`
- Modify: `backend/app/schemas/run.py`
- Test: `backend/tests/test_run_control.py`

- [ ] **Step 1: Write failing schema tests**

```python
from app.schemas.common import AgentStep
from app.schemas.run import ResearchConstraints, ResearchRun


def test_agent_step_has_resilience_defaults() -> None:
    step = AgentStep(name="literature_search")
    assert step.attempts == 0
    assert step.retryable is False
    assert step.skippable is False
    assert step.error_code is None
    assert step.events == []


def test_old_run_snapshot_remains_valid() -> None:
    run = ResearchRun.model_validate({
        "domain": "energy_materials",
        "question": "q",
        "constraints": ResearchConstraints().model_dump(),
        "steps": [{"name": "planner", "status": "completed", "summary": "ok"}],
    })
    assert run.resume_count == 0
    assert run.trust_warnings == []
    assert run.steps[0].attempts == 0
```

- [ ] **Step 2: Verify the tests fail before implementation**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_run_control.py -q`

Expected: failures for missing `attempts`, `resume_count`, and related fields.

- [ ] **Step 3: Add the run-control types**

```python
# backend/app/schemas/run_control.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


StepStatus = Literal[
    "pending", "running", "retrying", "completed",
    "waiting_action", "skipped", "failed", "paused",
]


class StepEvent(BaseModel):
    event: Literal["started", "retrying", "completed", "failed", "retried", "skipped", "recovered"]
    at: datetime
    detail: str = ""


class RunActionRequest(BaseModel):
    action: Literal["retry", "skip"]


class PaperPreviewRequest(BaseModel):
    paper_id: str
    source_url: str


class PaperPreviewResult(BaseModel):
    paper_id: str
    source_url: str
    kind: Literal["web_snapshot", "metadata_only"]
    title: str = ""
    screenshot_url: str | None = None
    original_url: str
    cached: bool = False
    error_summary: str | None = None
```

Extend `AgentStep` with defaults so existing stored snapshots still parse:

```python
attempts: int = 0
error_code: str | None = None
error_summary: str | None = None
retryable: bool = False
skippable: bool = False
events: list[StepEvent] = Field(default_factory=list)
```

Extend `ResearchRun`:

```python
resume_count: int = 0
trust_warnings: list[str] = Field(default_factory=list)
last_action: dict[str, Any] | None = None
```

- [ ] **Step 4: Run focused tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_run_control.py -q`

Expected: all Task 1 tests pass.

## Task 2: Implement Error Classification and One-Retry Step Execution

**Files:**

- Create: `backend/app/workflows/run_control.py`
- Modify: `backend/app/workflows/scientist_workflow.py`
- Modify: `backend/app/workflows/langgraph_workflow.py`
- Test: `backend/tests/test_run_control.py`

- [ ] **Step 1: Add failing policy and execution tests**

```python
import httpx
import pytest
from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.run_control import classify_step_error
from app.workflows.scientist_workflow import ScientistWorkflow, StepNeedsAction


def test_network_error_is_retryable() -> None:
    decision = classify_step_error(httpx.ReadTimeout("late"), "literature_search")
    assert decision.code == "temporary_network_error"
    assert decision.retryable is True


def test_validation_error_is_not_retryable() -> None:
    decision = classify_step_error(ValueError("missing baseline"), "baseline_intake")
    assert decision.retryable is False


@pytest.mark.asyncio
async def test_step_retries_once_then_completes(monkeypatch) -> None:
    workflow = ScientistWorkflow(Settings(dashscope_api_key=""))
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    calls = 0

    async def flaky(_run):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("temporary")

    await workflow._step(run, "literature_search", flaky)
    assert calls == 2
    assert run.steps[-1].status == "completed"
    assert run.steps[-1].attempts == 2


@pytest.mark.asyncio
async def test_second_retryable_failure_waits_for_action() -> None:
    workflow = ScientistWorkflow(Settings(dashscope_api_key=""))
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())

    async def always_fails(_run):
        raise httpx.ReadTimeout("temporary")

    with pytest.raises(StepNeedsAction):
        await workflow._step(run, "literature_search", always_fails)
    assert run.steps[-1].status == "waiting_action"
    assert run.steps[-1].attempts == 2
```

- [ ] **Step 2: Verify the focused tests fail**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_run_control.py -q`

Expected: import or assertion failures for the missing policy and retry behavior.

- [ ] **Step 3: Implement a narrow retry policy**

```python
# backend/app/workflows/run_control.py
from dataclasses import dataclass
import httpx

SKIPPABLE_STEPS = {"literature_mining", "paper_classification", "ablation_analysis"}


@dataclass(frozen=True)
class ErrorDecision:
    code: str
    retryable: bool
    summary: str


def classify_step_error(exc: Exception, step_name: str) -> ErrorDecision:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return ErrorDecision("temporary_network_error", True, "外部服务暂时不可用或请求超时")
    message = str(exc).lower()
    if any(token in message for token in ("429", "rate limit", "temporarily unavailable")):
        return ErrorDecision("temporary_service_error", True, "外部服务暂时限流或不可用")
    if step_name == "browser_capture":
        return ErrorDecision("browser_capture_error", True, "论文网页抓取暂时失败")
    return ErrorDecision("step_validation_error", False, str(exc) or "步骤执行失败")
```

Add `StepNeedsAction(Exception)` and change `_step` to attempt at most twice. On first retryable failure set `retrying`, append an event, persist the run, and immediately retry. On the second retryable failure set `waiting_action`, pause the run, and raise `StepNeedsAction`. For non-retryable failures set `waiting_action` without a blind retry.

- [ ] **Step 4: Preserve waiting state in both workflow entry points**

In `ScientistWorkflow.run`, `ScientistWorkflow.continue_run`, `LangGraphWorkflow.run`, and `LangGraphWorkflow.continue_run`, catch `StepNeedsAction` before the generic exception block:

```python
except StepNeedsAction:
    run.status = RunStatus.paused
    run.updated_at = utc_now()
```

The generic exception block remains responsible only for terminal failures.

- [ ] **Step 5: Run resilience and existing workflow tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_run_control.py backend/tests/test_workflow_mock.py backend/tests/test_langgraph_workflow.py -q`

Expected: new tests pass and existing workflow behavior remains green.

## Task 3: Add Retry, Skip, and Explicit Recovery APIs

**Files:**

- Modify: `backend/app/workflows/scientist_workflow.py`
- Modify: `backend/app/api/routes_runs.py`
- Create: `backend/tests/test_run_actions_api.py`

- [ ] **Step 1: Write failing endpoint tests**

```python
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.common import AgentStep, RunStatus
from app.schemas.run import ResearchConstraints, ResearchRun
from app.storage.in_memory import run_store

client = TestClient(app)


def waiting_run(step_name="literature_mining", *, skippable=True):
    run = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    run.status = RunStatus.paused
    run.current_stage = step_name
    run.steps = [AgentStep(name=step_name, status="waiting_action", attempts=2, retryable=True, skippable=skippable)]
    return run_store.create(run)


def test_skip_rejects_critical_step() -> None:
    run = waiting_run("report_writer", skippable=False)
    response = client.post(f"/api/runs/{run.run_id}/steps/report_writer/action", json={"action": "skip"})
    assert response.status_code == 409


def test_recover_requires_explicit_user_action() -> None:
    run = waiting_run()
    response = client.post(f"/api/runs/{run.run_id}/recover")
    assert response.status_code == 200
    assert response.json()["resume_count"] == 1
    assert response.json()["last_action"]["action"] == "recover"
```

- [ ] **Step 2: Verify endpoint tests fail**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_run_actions_api.py -q`

Expected: 404 responses for missing routes.

- [ ] **Step 3: Add stable action routes**

```python
@router.post("/{run_id}/steps/{step_name}/action", response_model=ResearchRun)
async def act_on_step(run_id: str, step_name: str, payload: RunActionRequest) -> ResearchRun:
    run = _must_get_run(run_id)
    step = next((item for item in reversed(run.steps) if item.name == step_name), None)
    if step is None or step.status != "waiting_action":
        raise HTTPException(status_code=409, detail="step is not waiting for action")
    if payload.action == "skip" and not step.skippable:
        raise HTTPException(status_code=409, detail="critical step cannot be skipped")
    return await build_workflow(get_settings()).resume_waiting_step(run, step, payload.action)


@router.post("/{run_id}/recover", response_model=ResearchRun)
async def recover_run(run_id: str) -> ResearchRun:
    run = _must_get_run(run_id)
    if run.status == RunStatus.completed:
        raise HTTPException(status_code=409, detail="completed run does not need recovery")
    return await build_workflow(get_settings()).recover_run(run)
```

- [ ] **Step 4: Implement controlled continuation**

Add `resume_waiting_step` and `recover_run` to `ScientistWorkflow`. They must:

- validate that the named step is the current waiting step;
- mark a skipped step and append a trust warning when it affects completeness;
- retry the exact step through the same `_step` policy;
- resume from the next stage using an explicit stage-to-tail dispatcher;
- never clear completed steps or restart the run from `intent_router`;
- convert orphaned `running` steps to `waiting_action` during recovery;
- increment `resume_count` and write `last_action`.

Use a dispatcher with named continuation functions rather than index arithmetic:

```python
CONTINUATIONS = {
    "citation_verification": "_run_after_citation_review",
    "literature_mining": "_resume_after_literature_mining",
    "paper_classification": "_resume_after_paper_classification",
    "ablation_analysis": "_resume_after_ablation_analysis",
}
```

Critical stages not present in the dispatcher cannot be skipped. Retrying a critical stage is allowed only when its agent method is registered in `STEP_METHODS`.

- [ ] **Step 5: Run API and regression tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_run_actions_api.py backend/tests/test_api_routes.py backend/tests/test_s6_workflow.py backend/tests/test_s5_langgraph_cycles.py -q`

Expected: action tests and existing nonlinear workflow tests pass.

## Task 4: Add Cached Paper Web Preview Fallback

**Files:**

- Modify: `backend/app/schemas/browser.py`
- Modify: `backend/app/api/routes_browser.py`
- Create: `backend/tests/test_paper_preview_api.py`

- [ ] **Step 1: Write failing preview tests**

```python
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_preview_uses_browser_worker_and_then_cache(monkeypatch, tmp_path) -> None:
    calls = 0

    async def fake_capture(self, payload):
        nonlocal calls
        calls += 1
        image = tmp_path / "trace.png"
        image.write_bytes(b"png")
        return type("Result", (), {
            "title": "Paper", "screenshot_path": str(image), "url": str(payload.url), "trace_id": "trace_1"
        })()

    monkeypatch.setattr("app.api.routes_browser.BrowserWorkerClient.capture", fake_capture)
    payload = {"paper_id": "p1", "source_url": "https://example.org/paper"}
    first = client.post("/api/browser/paper-preview", json=payload)
    second = client.post("/api/browser/paper-preview", json=payload)
    assert first.status_code == 200
    assert second.json()["cached"] is True
    assert calls == 1
```

- [ ] **Step 2: Verify preview tests fail**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_paper_preview_api.py -q`

Expected: missing-route failure.

- [ ] **Step 3: Implement preview cache and safe artifact serving**

Add `POST /api/browser/paper-preview`. Cache metadata in `DATA_DIR/browser_previews/<sha256>.json`, keyed by `paper_id + source_url`. Call browser-worker with `download_pdfs=False`. Return:

```json
{
  "paper_id": "p1",
  "source_url": "https://example.org/paper",
  "kind": "web_snapshot",
  "title": "Paper",
  "screenshot_url": "/api/browser/artifacts/trace_1.png",
  "original_url": "https://example.org/paper",
  "cached": false
}
```

Add `GET /api/browser/artifacts/{filename}`. Resolve only files directly under `DATA_DIR/browser_traces`, reject path separators and unknown extensions, and serve `.png` using `FileResponse`. On worker failure return a successful `metadata_only` response with `error_summary`; do not mark citation verification as failed.

- [ ] **Step 4: Run preview and browser tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_paper_preview_api.py backend/tests/test_api_routes.py -q`

Expected: preview cache, safe paths, and existing browser routes pass.

## Task 5: Add Frontend Types, API Calls, and Pure View Models

**Files:**

- Modify: `frontend/lib/api.ts`
- Create: `frontend/lib/workbench.ts`
- Create: `frontend/lib/workbench.test.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

- [ ] **Step 1: Install and configure the minimal test runner**

Run: `npm install --save-dev vitest`

Add to `frontend/package.json`:

```json
"test": "vitest run"
```

- [ ] **Step 2: Write failing view-model tests**

```typescript
import { describe, expect, it } from "vitest";
import { buildConversationMessages, groupRunStages, stepActions } from "./workbench";

describe("workbench view models", () => {
  it("shows retry and skip only for a skippable waiting step", () => {
    expect(stepActions({ status: "waiting_action", retryable: true, skippable: true })).toEqual(["retry", "skip"]);
    expect(stepActions({ status: "waiting_action", retryable: true, skippable: false })).toEqual(["retry"]);
  });

  it("groups experiment redesign into the experiment stage", () => {
    const groups = groupRunStages([{ name: "experiment_redesign", status: "completed", summary: "round 1" }]);
    expect(groups.find(group => group.id === "experiment")?.steps).toHaveLength(1);
  });

  it("creates a retry message from step history", () => {
    const messages = buildConversationMessages({
      steps: [{ name: "literature_search", status: "retrying", summary: "retry", attempts: 1 }],
      errors: [],
    });
    expect(messages[0].kind).toBe("warning");
  });
});
```

- [ ] **Step 3: Add frontend contracts**

Extend the `steps` item in `ResearchRun` with the Task 1 fields and add:

```typescript
export type RunStepAction = "retry" | "skip";
export type PaperPreviewResult = {
  paper_id: string;
  source_url: string;
  kind: "web_snapshot" | "metadata_only";
  title: string;
  screenshot_url?: string | null;
  original_url: string;
  cached: boolean;
  error_summary?: string | null;
};

export const actOnRunStep = (runId: string, stepName: string, action: RunStepAction) =>
  request<ResearchRun>(`/api/runs/${runId}/steps/${stepName}/action`, {
    method: "POST", body: JSON.stringify({ action }),
  });

export const recoverRun = (runId: string) =>
  request<ResearchRun>(`/api/runs/${runId}/recover`, { method: "POST" });

export const previewPaper = (paperId: string, sourceUrl: string) =>
  request<PaperPreviewResult>("/api/browser/paper-preview", {
    method: "POST", body: JSON.stringify({ paper_id: paperId, source_url: sourceUrl }),
  });
```

- [ ] **Step 4: Implement pure stage and conversation mapping**

`frontend/lib/workbench.ts` must export:

- `STAGE_GROUPS` for plan, literature, hypothesis, baseline, experiment, and report;
- `groupRunStages(steps)` preserving backend order;
- `buildConversationMessages(run)` for start, progress, retry, waiting, completion, and error messages;
- `stepActions(step)` which never exposes skip for a critical step.

- [ ] **Step 5: Run frontend unit tests**

Run: `npm test`

Expected: all workbench helper tests pass.

## Task 6: Build the Three Focused Workbench Panes

**Files:**

- Create: `frontend/components/workbench/ResearchConversation.tsx`
- Create: `frontend/components/workbench/ResearchStageNavigator.tsx`
- Create: `frontend/components/workbench/ResearchStageContent.tsx`
- Modify: `frontend/components/workbench/PaperReaderPanel.tsx`

- [ ] **Step 1: Implement the conversation pane**

Define focused props rather than passing the entire `Workbench` state:

```typescript
type Props = {
  run: ResearchRun | null;
  question: string;
  busy: boolean;
  error: string;
  onQuestionChange(value: string): void;
  onStart(): void;
  onStepAction(stepName: string, action: RunStepAction): void;
};
```

Render the existing research settings above a chat-style timeline. The submit button calls `onStart` directly. Waiting-action messages render buttons returned by `stepActions`; no confirmation dialog is introduced.

- [ ] **Step 2: Implement the stage navigator**

Render the seven user-facing stages from the design while the helper internally groups them into stable IDs. Each stage shows aggregate status, completed/total count, and the latest summary. The experiment stage shows `experiment_redesign_round` as `重设计第 N 轮`.

- [ ] **Step 3: Implement stage content composition**

Move existing panel composition out of `Workbench.tsx`. `ResearchStageContent` receives the active stage plus the existing callbacks and renders only relevant panels. It must reuse, not duplicate, `LiteratureBoard`, `BaselineBoard`, experiment panels, feedback loop, claim audit, and report viewer.

- [ ] **Step 4: Implement PDF-first paper fallback**

Change `PaperReaderPanel` props:

```typescript
type Props = {
  paper: Paper | null;
  preview: PaperPreviewResult | null;
  loading: boolean;
  error: string;
  onRetryPreview(): void;
};
```

Behavior order:

1. Embed `paper.pdf_url` when present.
2. Otherwise show the cached or newly requested screenshot using `${API_BASE}${preview.screenshot_url}`.
3. On `metadata_only`, show the abstract, error summary, original link, and a retry button.
4. Always keep an external source link available.

- [ ] **Step 5: Run unit tests and type checking**

Run: `npm test`

Run: `npx tsc --noEmit`

Expected: tests and TypeScript checks pass.

## Task 7: Recompose Workbench and Add Responsive Three-Pane CSS

**Files:**

- Modify: `frontend/components/workbench/Workbench.tsx`
- Modify: `frontend/components/workbench/RunHistory.tsx`
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Make history selection explicit**

Remove the automatic `setRun(nextRuns[0])` behavior from `loadInitialData`. Load the list but keep `run` null until the user starts a task or selects history. In `RunHistory`, show status, last stage, updated time, and a clear “打开/恢复” action.

- [ ] **Step 2: Add workbench orchestration state**

Keep only shared orchestration in `Workbench.tsx`:

```typescript
const [activeStage, setActiveStage] = useState("plan");
const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
const [paperPreview, setPaperPreview] = useState<PaperPreviewResult | null>(null);
const [paperPreviewBusy, setPaperPreviewBusy] = useState(false);
const [mobilePane, setMobilePane] = useState<"conversation" | "workflow" | "paper">("workflow");
```

Add `handleStepAction`, `handleRecoverRun`, and `loadPaperPreview`. Selecting a paper with no PDF automatically calls `loadPaperPreview`; switching to another paper cancels stale state by comparing the selected paper ID before applying the result.

- [ ] **Step 3: Compose the three panes**

Use semantic structure:

```tsx
<main className="research-workbench">
  <aside className="conversation-pane">...</aside>
  <section className="workflow-pane">...</section>
  <aside className="paper-pane">...</aside>
</main>
```

The middle pane contains the status strip, stage navigator, and stage content. The right pane remains mounted so paper selection does not lose preview state.

- [ ] **Step 4: Add responsive CSS**

Desktop:

```css
.research-workbench {
  height: 100vh;
  display: grid;
  grid-template-columns: minmax(300px, 360px) minmax(520px, 1fr) minmax(360px, 32vw);
  overflow: hidden;
}
.conversation-pane, .workflow-pane, .paper-pane { min-width: 0; overflow-y: auto; }
```

At widths below `1180px`, turn the paper pane into a toggleable right drawer. At widths below `760px`, show one pane at a time with a sticky three-tab switcher. Preserve keyboard focus and do not use `display:none` for the currently active pane.

- [ ] **Step 5: Verify frontend behavior**

Run: `npm test`

Run: `npx tsc --noEmit`

Run: `npm run build`

Expected: unit tests, type checks, and production build pass.

## Task 8: Documentation, Full Regression, and Docker Verification

**Files:**

- Modify: `docs/API.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `README.md`

- [ ] **Step 1: Document the new contracts**

Add exact request/response examples for:

- `POST /api/runs/{run_id}/steps/{step_name}/action`
- `POST /api/runs/{run_id}/recover`
- `POST /api/browser/paper-preview`
- `GET /api/browser/artifacts/{filename}`

Document that history recovery is user-selected, only one automatic retry occurs, preview snapshots do not affect citation verification, and baseline remains manual or AI-generated.

- [ ] **Step 2: Run the complete backend suite**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -q`

Expected: all backend tests pass; only previously known warnings may remain.

- [ ] **Step 3: Run the complete frontend verification**

Run from `frontend`:

```powershell
npm test
npx tsc --noEmit
npm run build
```

Expected: all three commands exit successfully.

- [ ] **Step 4: Perform diff hygiene checks**

Run: `git diff --check`

Expected: no whitespace errors. CRLF conversion notices are acceptable if they do not indicate content corruption.

- [ ] **Step 5: Build and start Docker services**

Run: `docker compose up --build -d`

Run: `docker compose ps`

Expected: frontend, backend, and browser-worker all report healthy.

- [ ] **Step 6: Verify service and preview health**

Run HTTP checks for:

- `http://localhost:3000` → 200
- `http://localhost:8000/health` → 200
- `http://localhost:8010/health` → 200
- `POST http://localhost:8000/api/browser/paper-preview` with a stable public paper URL → `web_snapshot` or the explicit `metadata_only` fallback.

- [ ] **Step 7: Run one end-to-end research task**

Create a seismic run using an AI-generated baseline, start it, poll until completion or a waiting-action state, select a paper preview, and verify:

- baseline provenance is `ai_generated`;
- no automatic external baseline discovery step appears in the main route;
- experiment redesign round is visible if the poor-result gate triggers;
- final report contains provenance and limitations;
- a controlled transient failure produces exactly one automatic retry.

## Plan Self-Review

- Spec coverage: three-pane layout, direct execution, one automatic retry, retry/skip actions, user-selected recovery, paper preview fallback, baseline constraints, experiment redesign visibility, responsive behavior, tests, and Docker verification are each mapped to a task.
- Placeholder scan: no open implementation placeholders remain.
- Type consistency: backend `RunActionRequest`, `PaperPreviewResult`, enriched `AgentStep`, and frontend equivalents use the same field names and action literals.
- Scope: no task queue, SSE/WebSocket, authentication, cloud sync, or unrelated Agent rewrite is included.
- Repository safety: no commit, reset, cleanup, or overwrite of unrelated existing changes is planned.
