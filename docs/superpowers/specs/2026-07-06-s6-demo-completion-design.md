# TrustSci-Agent S6 Demo Completion Design

## Goal

Stabilize the current S1-S5 workspace as a reproducible contest-demo baseline, then complete S6 by making all three research modes behaviorally distinct, adding experiment-assistance analysis, exposing a compact V3 API surface, and extending report provenance.

All changes remain in the local worktree. No Git commit is created.

## Scope

### Baseline repairs

- Recreate the broken `backend/.venv` from the available Python 3.11 interpreter and install `backend/requirements.txt`.
- Restore `.env.example` with safe, non-secret defaults matching `Settings` and Docker Compose.
- Update README and architecture documentation so the documented primary V3 path is seismic-event classification with LangGraph, while retaining the classic energy-materials path as a compatibility mode.
- Add a deterministic environment check that reports Python dependencies, Node availability, optional Docker availability, workflow engine, and whether Qwen is configured without printing secrets.
- Harden generated-code execution with AST validation, a dangerous-import and dangerous-call denylist, isolated interpreter mode, a minimal subprocess environment, timeout enforcement, and explicit audit output.

### S6 features

- Complete the three research modes: `discovery`, `idea_refinement`, and `experiment_assistance`.
- Add structured experiment-assistance input and three structured analysis outputs.
- Add a compact V3 summary API for the demonstration UI.
- Extend report provenance with Arena, baseline, experiment iteration, debugging, ablation, and result-support information.
- Add frontend input and result panels for experiment assistance and the new report analyses.

## Non-goals

- No database, Redis, Celery, authentication, multi-tenant isolation, or deployment hardening.
- No execution of code supplied through experiment-assistance input.
- No OS-level or container-per-run sandbox; that remains an S7 hardening item.
- No redesign of the complete workbench or unrelated decomposition of existing large files.
- No claim that the synthetic seismic dataset represents real waveform validation.

## Architecture

The existing `ResearchRun` remains the single workflow state object. LangGraph remains responsible for branching, feedback loops, and guided checkpoints; inherited `ScientistWorkflow` step methods remain responsible for domain work. S6 adds focused schemas and agents rather than adding more responsibilities to the existing report writer.

Mode routing becomes behavioral instead of cosmetic:

```text
discovery
  intent -> planner -> literature/evidence -> arena -> novelty/baseline gates
  -> experiment design -> generated-code experiment -> result analysis -> report

idea_refinement
  idea intake -> planner -> literature/evidence -> arena refinement -> novelty/baseline gates
  -> experiment design -> generated-code experiment -> result analysis -> report

experiment_assistance
  assistance input -> intent/planner -> optional literature/evidence context
  -> normalize supplied results -> result evaluation -> ablation analysis
  -> result interpretation -> report
```

The experiment-assistance branch never calls `CodeWriterAgent` or `SandboxExecutor`.

## Data Model

Create `backend/app/schemas/experiment_assistance.py` with:

- `MetricObservation`: metric name, value, optional unit, split, and notes.
- `AblationObservation`: component removed or changed, metrics, and notes.
- `ExperimentAssistanceInput`: objective, method summary, optional source code, dataset description, baseline name, baseline metrics, method metrics, ablations, logs, and author notes.
- `ResultEvaluation`: `pass`, `partial`, or `fail`; supported and unsupported claims; metric deltas; data-quality warnings; reasoning.
- `AblationFinding` and `AblationAnalysis`: component effects, coverage status, missing comparisons, and summary.
- `ResultInterpretation`: conclusions, limitations, failure explanation, next experiments, and evidence boundary.

Add optional `experiment_assistance`, `result_evaluation`, `ablation_analysis`, and `result_interpretation` fields to `ResearchRun`.

The API accepts assistance data only for a run whose mode is `experiment_assistance`. Required semantic content is the objective plus at least one method metric or experiment log. Source code is stored as text for review and provenance but is never imported or executed.

## Agents

Add three agents following the existing LCEL plus deterministic-fallback pattern:

- `ResultEvaluatorAgent` compares supplied method and baseline metrics, labels the result, and separates measured support from author interpretation.
- `AblationAgent` summarizes supplied ablations and explicitly reports insufficient coverage when no controlled ablation exists.
- `ResultInterpreterAgent` converts evaluation and ablation findings into bounded scientific conclusions, limitations, and next experiments.

Each agent receives only structured run data and returns a validated Pydantic model. Invalid LLM output falls back to deterministic analysis. The deterministic path must remain useful when `DASHSCOPE_API_KEY` is absent.

For discovery and idea-refinement modes, these agents consume `CodeExperimentResult`. For experiment assistance, they consume `ExperimentAssistanceInput`.

## Workflow Changes

Replace the three passthrough mode nodes with explicit branch-entry behavior:

- Discovery preserves the current automatic path.
- Idea refinement requires `IdeaIntakeAgent` output and carries the idea constraints into planning and Arena scoring.
- Experiment assistance validates attached input and routes around Arena code generation and automatic experiment execution. Literature retrieval remains available as contextual support, but absence of live literature must not prevent analysis of supplied results.

Add result evaluation, ablation analysis, and result interpretation immediately before report generation in all modes. Existing S5 loop counters and routing caps remain unchanged.

Guided citation and evidence pauses continue to work. Experiment-assistance mode may proceed with zero retrieved papers, but the report must then mark literature support as unavailable rather than manufacturing citations.

## API

Add:

- `POST /api/runs/{run_id}/experiment-assistance` to validate and attach structured input before the run starts.
- `GET /api/runs/{run_id}/v3-summary` to return a compact, stable demonstration payload containing mode, status, current stage, progress, selected hypothesis, novelty verdict, baseline gate, experiment outcome, result evaluation, loop counters, warnings, and report readiness.

Keep `GET /api/runs/{run_id}` as the canonical complete state response. Existing endpoints remain backward-compatible.

API errors:

- `404` when the run does not exist.
- `409` when assistance input is attached to the wrong mode or after execution has started.
- `422` when objective/evidence requirements or metric values are invalid.
- Workflow analysis failures are recorded in `run.errors`; deterministic fallbacks prevent recoverable LLM-format failures from failing the run.

## Frontend

Extend the experiment-assistance draft with fields for objective, method summary, dataset, baseline and method metrics, logs, optional code, and optional ablation rows. Small `.json`, `.txt`, `.log`, and `.py` files may be read by the browser into these text fields; the backend still receives JSON rather than multipart uploads.

When starting an experiment-assistance run, the frontend creates the run, attaches assistance input, and then starts it. If attachment fails, it must not start the run.

Add focused panels for:

- Result support judgment.
- Ablation findings and missing comparisons.
- Result interpretation, limitations, and recommended next experiments.

Existing discovery and seismic panels remain intact.

## Report Provenance

Extend report provenance with optional structured sections:

- Arena report and selected-hypothesis rationale.
- Baseline origin and comparison grade.
- Experiment iteration and macro/switchback history.
- Code debug summary without embedding uncontrolled full tracebacks.
- Ablation report.
- Result-support judgment and evidence boundary.

Report language must distinguish measured results, deterministic demo outputs, expected results, and unsupported claims. Experiment-assistance reports identify all supplied measurements as user-provided unless independently reproduced by the system.

## Generated-code Safety

Before writing `model.py`, parse it with `ast.parse` and reject:

- imports including `os`, `sys`, `subprocess`, `socket`, `requests`, `httpx`, `urllib`, `pathlib`, `shutil`, `ctypes`, `multiprocessing`, and package-management modules;
- calls including `open`, `eval`, `exec`, `compile`, `__import__`, `input`, and process/shell launchers;
- dunder attribute traversal and dynamic import patterns.

The executor launches `sys.executable -I` with a minimal environment and an isolated working directory. The fixed harness remains the only executable entrypoint. Validation rejection becomes a normal failed experiment result that can enter the existing repair loop.

This is defense in depth for a local contest demo, not a security boundary.

## Testing

Use test-driven development for every behavior change:

- schema validation and JSON round trips;
- assistance input API success and 404/409/422 cases;
- distinct LangGraph routing for all three modes;
- proof that experiment assistance never invokes the code writer or sandbox;
- deterministic evaluation, ablation, and interpretation outputs;
- LLM malformed-output fallback;
- report provenance population and measured/expected-result wording;
- AST rejection and allowed sklearn/numpy model acceptance;
- V3 summary response shape;
- frontend TypeScript production build.

Final verification requires a fresh backend virtual environment, the full backend pytest suite with zero failures, the frontend production build, and a deterministic no-key experiment-assistance smoke run.

## Acceptance Criteria

1. A new developer can recreate the backend environment from repository instructions without relying on the stale virtual environment.
2. Existing S1-S5 tests pass in the repaired environment.
3. Each research mode follows a distinct tested route.
4. Experiment assistance accepts structured existing results and produces evaluation, ablation, interpretation, and a report without executing submitted code.
5. The compact V3 summary exposes the complete demo story without frontend inference over dozens of fields.
6. Generated code is rejected before execution when it contains denied imports or calls.
7. Reports preserve provenance and clearly label user-provided, executed, expected, and unsupported results.
8. Frontend production build succeeds.
