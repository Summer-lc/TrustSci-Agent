# TrustSci-Agent Architecture

> Current-code note (2026-08-21): this file is a compact technical summary. New team members should also read the verified Chinese [architecture guide](onboarding/02_ARCHITECTURE.md), [runtime flow](onboarding/03_RUNTIME_FLOW.md), and [project status](onboarding/01_PROJECT_STATUS.md). When historical sprint wording differs from current routes or workflow code, current code is authoritative.

TrustSci-Agent is a Qwen-compatible multi-agent AI Scientist MVP. It is optimized for the contest requirement: generate a standardized, verifiable scientific hypothesis and research plan from literature/data inputs.

## Runtime Services

- `frontend`: Next.js research workbench.
- `backend`: FastAPI agent orchestrator and APIs.
- `browser-worker`: lightweight webpage capture service inspired by Hermes-style browser tooling.

## V3 Agent Flow

```text
Research Question
  -> Intent Router (discovery | idea_refinement | experiment_assistance)
  -> Planner Agent
  -> Literature Search Tool
  -> Citation Verifier Agent
  -> Evidence Ledger
  -> Gap Finder Agent
  -> Hypothesis Generator Agent
  -> Critic Agent
  -> Experiment Designer Agent
  -> Result Evaluator / Ablation / Result Interpreter
  -> Report Writer Agent
```

## Trust Controls

- The report writer receives only papers already present in the run state.
- Crossref verification checks DOI and title similarity.
- The evidence ledger binds each claim to a paper and verification state.
- The final report includes a citation audit log.
- The system runs without an LLM key in deterministic demo mode, but can call Bailian/Qwen through an OpenAI-compatible endpoint when configured.

## Primary Demo Domain

The primary V3 contest route is seismic-event classification. The bundled waveform harness is synthetic and supports reproducible software validation only; it is not evidence of real-world seismic performance. The energy-materials route remains available as the classic compatibility workflow.

Generated `model.py` is AST-validated and executed through a whitelisted local harness with a timeout and isolated interpreter flags. This is defense in depth for a local demo, not an OS-level security boundary.

## Baseline and Result Feedback Update

The main V3 seismic workflow no longer treats GitHub, Papers with Code, or paper-declared code links as the trusted baseline source. Baseline provenance is selected before execution: user-provided baseline, AI-generated local demo baseline, or no baseline. Legacy baseline discovery code may remain for manual debugging, but it is not part of the main trust loop.

When executable code completes with a clearly poor result, the workflow now routes through experiment redesign before rerunning the local harness. Code-level failures can still be handled by the existing micro repair loop, but scientific underperformance is treated as an experiment-design problem and is reported with explicit limitations.

## Workbench and Run Resilience

The frontend is organized into three independently scrolling panes:

- research conversation, direct execution controls, and user-selected history;
- grouped workflow stages and the stage's current artifacts;
- PDF-first paper reading with a browser-worker snapshot fallback.

`AgentStep` stores attempts, stable error metadata, action permissions, and an event history. The workflow wrapper automatically retries only transient failures and only once. A second transient failure, or a deterministic input/validation failure, moves the step to `waiting_action`. Retry and allowed skip actions are recorded before the incomplete pipeline resumes; already completed stages are not executed again.

Run recovery is explicit. Selecting recovery converts an orphaned `running` step to `waiting_action` while preserving completed artifacts and provenance. Paper-page capture is isolated from scholarly verification: failure to capture a page never downgrades or upgrades the citation state.
