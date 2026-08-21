# Workbench Clarity and Paper Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the workbench hierarchy, prevent Baseline content clipping, and replace automatic paper-page capture with fast PDF-first reading and explicit challenge fallback.

**Architecture:** Keep the existing three-pane workbench, but make readiness and stage navigation progressive-disclosure controls. Resolve paper reading targets with a pure frontend helper, invoke webpage capture only on demand, and let the browser worker report access challenges to the backend preview API.

**Tech Stack:** Next.js, React, TypeScript, Vitest, FastAPI, Pydantic, Playwright, Pytest, Docker Compose.

---

### Task 1: Lock frontend behavior with failing tests

**Files:**
- Modify: `frontend/lib/workbench.test.ts`
- Create: `frontend/components/workbench/WorkbenchLayout.test.tsx`

- [ ] Add tests for arXiv/direct-PDF resolution and source-only fallback.
- [ ] Add render tests requiring a collapsible readiness summary, compact inactive stages, and full-width Baseline panels.
- [ ] Run focused Vitest tests and confirm failures are caused by missing behavior.

### Task 2: Lock challenge fallback with a failing API test

**Files:**
- Modify: `backend/tests/test_paper_preview_api.py`

- [ ] Add a browser-worker response containing `blocked_reason`.
- [ ] Assert the preview API returns `metadata_only`, omits the screenshot, and provides a human-readable fallback.
- [ ] Run the focused Pytest test and confirm it fails before implementation.

### Task 3: Implement the frontend hierarchy and PDF-first reader

**Files:**
- Modify: `frontend/lib/workbench.ts`
- Modify: `frontend/components/workbench/Workbench.tsx`
- Modify: `frontend/components/workbench/PaperReaderPanel.tsx`
- Modify: `frontend/components/workbench/CompetitionReadinessPanel.tsx`
- Modify: `frontend/components/workbench/ResearchStageNavigator.tsx`
- Modify: `frontend/components/workbench/BaselineIntakePanel.tsx`
- Modify: `frontend/components/workbench/BaselineBoard.tsx`
- Modify: `frontend/app/globals.css`

- [ ] Implement the pure paper target resolver.
- [ ] Remove automatic preview capture and retain the manual snapshot action.
- [ ] Convert readiness to a collapsed details summary and compact the stage navigator.
- [ ] Make Baseline panels full width and add long-text wrapping styles.
- [ ] Run focused tests until green.

### Task 4: Implement fast challenge-aware capture

**Files:**
- Modify: `backend/app/schemas/browser.py`
- Modify: `backend/app/api/routes_browser.py`
- Modify: `backend/app/tools/browser_client.py`
- Modify: `browser-worker/worker.py`

- [ ] Add `blocked_reason` to the capture contract.
- [ ] Detect common challenge titles and HTML markers before taking a screenshot.
- [ ] Reduce navigation and client timeouts for preview capture.
- [ ] Return and cache a metadata-only result when access is blocked.
- [ ] Run focused backend tests until green.

### Task 5: Verify the completed behavior

**Files:**
- Verify only; no new production files.

- [ ] Run all frontend tests, TypeScript checking, and production build.
- [ ] Run all backend tests.
- [ ] Rebuild Docker images temporarily and inspect the workbench at desktop and mobile widths.
- [ ] Confirm no automatic capture request occurs when selecting a source-only paper.
- [ ] Stop all containers after verification so the project remains paused.
