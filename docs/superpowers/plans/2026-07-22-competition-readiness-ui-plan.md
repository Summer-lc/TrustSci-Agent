# Competition Readiness UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an evidence-based competition-readiness view model and present it in a polished, responsive three-pane research workbench.

**Architecture:** Keep readiness calculation in a pure frontend module so it is deterministic and testable. Render the result through one focused component and integrate it above the existing stage navigator. Limit CSS changes to tokens and workbench-specific selectors.

**Tech Stack:** Next.js, React, TypeScript, Vitest, CSS, lucide-react

---

### Task 1: Readiness view model

**Files:**
- Modify: `frontend/lib/workbench.ts`
- Modify: `frontend/lib/workbench.test.ts`

- [ ] Add failing tests for empty, demo-data and submission-ready runs.
- [ ] Run the focused test and confirm the new imports or assertions fail.
- [ ] Implement `buildCompetitionReadiness` and conservative dataset classification.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Readiness component

**Files:**
- Create: `frontend/components/workbench/CompetitionReadinessPanel.tsx`
- Modify: `frontend/components/workbench/Workbench.tsx`

- [ ] Render the overall state, completion count and five readiness checks.
- [ ] Integrate the panel between `StatusStrip` and `ResearchStageNavigator`.
- [ ] Ensure no action is presented as complete when facts are missing.

### Task 3: Visual system and responsive layout

**Files:**
- Modify: `frontend/app/globals.css`

- [ ] Refine color tokens, page background, panels and primary controls.
- [ ] Make the stage navigator six columns on wide screens, three on medium screens and two on mobile.
- [ ] Add responsive readiness cards without horizontal overflow.
- [ ] Preserve the three-pane desktop and drawer/mobile behavior.

### Task 4: Verification

**Files:**
- No production file changes expected.

- [ ] Run `npm test -- --run`.
- [ ] Run `npx tsc --noEmit`.
- [ ] Run `npm run build`.
- [ ] Start the local stack only for visual QA, inspect desktop and narrow layouts, then stop it again.
