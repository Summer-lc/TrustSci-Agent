# Resumable Run Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace numeric history labels with research names and add safe pause, resume, abandon, and cross-restart continuation.

**Architecture:** Extend the persisted `ResearchRun` lifecycle model and expose three control endpoints. Apply control actions at shared workflow step boundaries, then connect them to a unified history UI that handles in-memory runs and workspace snapshots.

**Tech Stack:** FastAPI, Pydantic, async Python workflows, Next.js, React, TypeScript, Vitest, Pytest.

---

### Task 1: Persist lifecycle metadata

**Files:**
- Modify: `backend/app/schemas/common.py`
- Modify: `backend/app/schemas/run.py`
- Modify: `backend/app/api/routes_runs.py`
- Test: `backend/tests/test_api_routes.py`

- [ ] Add failing tests for generated `display_name`, pause metadata, and abandoned status.
- [ ] Run the focused Pytest cases and confirm failures are caused by missing fields/status.
- [ ] Add `abandoned`, `display_name`, `control_action`, and `pause_reason` with backward-compatible defaults.
- [ ] Generate names from normalized research questions during creation.
- [ ] Run focused tests until green.

### Task 2: Add pause, resume, and abandon APIs

**Files:**
- Modify: `backend/app/api/routes_runs.py`
- Modify: `backend/app/workflows/scientist_workflow.py`
- Test: `backend/tests/test_api_routes.py`
- Test: `backend/tests/test_workflow_control.py`

- [ ] Write failing API tests for valid and invalid lifecycle transitions.
- [ ] Write failing workflow tests proving pause/abandon survives the current step and blocks later steps.
- [ ] Add control endpoints, persisted audit metadata, and explicit 409 errors for invalid transitions.
- [ ] Add shared workflow control signals and a user-resume entry point based on `_resume_incomplete_pipeline`.
- [ ] Run lifecycle and workflow tests until green.

### Task 3: Make workspace recovery lifecycle-aware

**Files:**
- Modify: `backend/app/storage/workspace.py`
- Test: `backend/tests/test_workspace.py`

- [ ] Add failing tests for old snapshots without names and pause requests interrupted by process restart.
- [ ] Normalize legacy names and convert persisted `running + pause` snapshots to `paused + user` during restore.
- [ ] Run workspace tests until green.

### Task 4: Add typed frontend lifecycle clients

**Files:**
- Modify: `frontend/lib/api.ts`
- Test: `frontend/lib/workbench.test.ts`

- [ ] Add failing tests for history-name and lifecycle-label helpers.
- [ ] Extend `ResearchRun` and `RestorableWorkspace` types and add pause/resume/abandon request functions.
- [ ] Add pure name/status/action helpers to `frontend/lib/workbench.ts`.
- [ ] Run focused Vitest tests until green.

### Task 5: Redesign history actions

**Files:**
- Modify: `frontend/components/workbench/RunHistory.tsx`
- Modify: `frontend/components/workbench/Workbench.tsx`
- Modify: `frontend/components/workbench/WorkbenchLayout.test.tsx`
- Modify: `frontend/app/globals.css`

- [ ] Add failing static-render tests asserting concrete names and lifecycle actions with no visible `run_id`.
- [ ] Render unified run/workspace history rows with stage, time, pause, resume, restore, and abandon controls.
- [ ] Wire handlers in `Workbench`, including restore-then-resume and destructive confirmation.
- [ ] Add compact action styles and responsive behavior.
- [ ] Run focused component tests until green.

### Task 6: Full verification

**Files:**
- Verify only.

- [ ] Run `pytest -q` in `backend` and confirm zero failures.
- [ ] Run `npm test`, `npx tsc --noEmit`, and `npm run build` in `frontend`.
- [ ] Rebuild Docker images, exercise pause/resume/abandon against the live API, and verify the UI at desktop and mobile widths.
- [ ] Leave the project stopped after verification unless the user explicitly requests it to remain running.
