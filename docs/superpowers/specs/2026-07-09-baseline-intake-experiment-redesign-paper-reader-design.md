# TrustSci-Agent Baseline Intake, Experiment Redesign, and Paper Reader Design

## Goal

Replace the current automatic baseline-mining path with an explicit user-selected baseline strategy, make poor executable results trigger experiment redesign instead of primarily repairing or switching hypotheses, and add a lightweight right-side paper reader in the frontend literature view.

All changes remain in the local worktree. No Git commit is created.

## User Decisions

- Baseline strategy is selected before a run starts.
- The available baseline strategies are:
  - `manual_upload`: the user supplies baseline metadata, metrics, and optional code text or repository link.
  - `ai_generated`: the system creates a simple demo baseline and labels it as AI-generated, not as SOTA or externally verified.
  - `none`: the run proceeds without a baseline and reports the comparison limitation.
- The paper reader starts as the lightweight version: metadata, abstract, source/PDF links, and PDF iframe when available. Browser-worker preview can be added later.

## Non-goals

- Do not keep automatic GitHub, Papers with Code, or paper-code-link mining in the main baseline trust loop.
- Do not claim that an AI-generated baseline is a literature SOTA baseline.
- Do not build a full PDF annotation system, citation manager, or browser-worker powered reader in this iteration.
- Do not remove legacy baseline discovery code unless it blocks the new main flow. It can remain as debug or deprecated API surface.
- Do not change experiment-assistance behavior to execute user-submitted code.

## Current Problems

The current seismic workflow routes through:

```text
extract_code_urls -> baseline_discover -> baseline_verify -> baseline_quality_gate
```

That path infers baseline candidates from papers, code links, GitHub, and Papers with Code. It is convenient for an automated demo, but it creates a trust problem: found repositories may be unrelated, dataset-only, stale, not runnable, or not actually comparable. For a contest demo, an explicit baseline source is easier to defend.

The current poor-result handling routes through `macro_react`: failed or clearly negative results can trigger macro code repair or switchback to another Arena hypothesis. That treats poor experimental performance as a code/hypothesis issue before asking whether the experiment design itself is weak.

The current literature UI has external source and PDF links, but it does not let the user inspect a selected paper in the right-side workspace context.

## Architecture

Keep `ResearchRun` as the central state object. Add a baseline strategy and baseline intake output to the run state, and route the workflow through a new baseline-intake step instead of automatic baseline discovery.

Recommended high-level seismic path:

```text
intent_router
-> planner
-> literature_search
-> citation_verification
-> evidence_ledger
-> literature_mining
-> paper_classification
-> scientific_data_profile
-> arena
-> novelty_check
-> baseline_intake
-> baseline_quality_gate
-> experiment_design
-> code_experiment
-> experiment_result_gate
-> experiment_redesign?        # at most once by default
-> code_experiment?
-> result_evaluation
-> ablation_analysis
-> result_interpretation
-> report_writer
-> claim_verification
-> report_revision
-> claim_reverification
-> report_translation
```

`extract_code_urls`, `baseline_discover`, and `baseline_verify` leave the main LangGraph path. The legacy functions may remain callable from existing manual API endpoints until a later cleanup.

## Baseline Data Model

Add a focused schema module at `backend/app/schemas/baseline_intake.py` with:

- `BaselineStrategy`: `manual_upload | ai_generated | none`
- `ManualBaselineInput`
  - name
  - description
  - optional code text
  - optional repository URL
  - optional run command
  - dataset description
  - metrics
  - notes
- `BaselineIntake`
  - strategy
  - source_type: `manual_upload | ai_generated | unavailable`
  - trust_level: `user_provided | runnable_demo | insufficient`
  - name
  - description
  - metrics
  - limitations
  - provenance notes

Add optional fields to `ResearchRun`:

- `baseline_strategy`
- `manual_baseline`
- `baseline_intake`

Keep `baseline_candidates` for compatibility, but the main run path should no longer fill it by searching papers or code repositories.

## Baseline API

Add an endpoint for pre-start baseline selection:

```text
POST /api/runs/{run_id}/baseline-intake
```

Rules:

- Only allowed while `run.status == created`.
- Accepts one of the three strategies.
- For `manual_upload`, require at least a baseline name plus either metrics, code text, repository URL, or notes.
- For `ai_generated`, no user payload is required beyond the strategy.
- For `none`, no user payload is required.
- Return `409` if attached after the run has started.
- Return `422` for invalid manual baseline content.

The frontend should attach this payload between `createRun()` and `startRun()`, similar to experiment assistance.

## Baseline Agent Behavior

Add a `BaselineIntakeAgent` or equivalent workflow method:

- `manual_upload`: normalize user input into `BaselineIntake`, mark source as user-provided, and do lightweight validation. Do not run arbitrary uploaded code.
- `ai_generated`: create a simple reproducible baseline description that points to the fixed local seismic harness baseline behavior. This is a demo baseline, not an externally verified baseline. It should not introduce a second generated baseline execution path in this iteration; the executable comparison remains the existing harness baseline inside `train.py`.
- `none`: create an `unavailable` intake record with comparison limitations.

Update `baseline_quality_gate` so it evaluates `baseline_intake` first:

- `manual_upload`: pass the run gate if sufficient metrics or runnable metadata exist; research-grade remains limited unless the user explicitly provides evidence of external verification.
- `ai_generated`: pass the run gate for local comparison, but mark research-grade as degraded.
- `none`: fail comparison gate and mark comparison grade degraded.

## Experiment Redesign

Add a result gate after `code_experiment`.

The result gate separates engineering failures from scientific underperformance:

- If tests fail, model code is invalid, or `train.py` crashes: keep the existing micro repair behavior inside `code_experiment`.
- If the experiment completes but is meaningfully worse than baseline, route to `experiment_redesign`.
- If the result is positive or only narrowly negative, proceed to result analysis.

Add `experiment_redesign_round` to `ResearchRun`, capped at 1 by default for demo stability.

Add an `ExperimentRedesignAgent` or workflow method that consumes:

- selected hypothesis
- current experiment plan
- code experiment summary
- comparison metrics
- debug notes
- baseline intake

It produces a revised `ExperimentPlan` with:

- a short redesign rationale
- changed features/model/metrics/data split assumptions
- expected failure modes
- what will be tested differently

The second `code_experiment` run uses the redesigned experiment plan. If the second result is still poor, the workflow proceeds to result analysis and report with a clear negative or partial conclusion.

Keep the existing `macro_react` method name for compatibility in this iteration, but change its routing responsibility: completed poor results route to `experiment_redesign`; code-level failures may still use macro repair if the existing micro repair loop cannot produce a runnable model. A later cleanup can rename `macro_react` after tests and UI labels no longer depend on it.

## LangGraph Routing

Update the LangGraph seismic branch:

```text
novelty_check -> baseline_intake -> baseline_quality_gate -> experiment_design
```

Remove these main-path edges:

```text
novelty_check -> extract_code_urls -> baseline_discover -> baseline_verify
```

Add:

```text
code_experiment -> experiment_result_gate
experiment_result_gate -> experiment_redesign | result_evaluation
experiment_redesign -> code_experiment
```

The classic workflow should mirror the same behavior so tests and local fallback runs remain consistent.

## Frontend Baseline UX

In the seismic research console draft area, add a baseline strategy control:

- Manual baseline
- AI generated demo baseline
- No baseline

For manual baseline, show fields for name, description, dataset, metrics, repository URL, run command, optional code text, and notes. Keep this JSON/text-based rather than multipart upload for this iteration. A later iteration can add file upload and zip handling.

For AI-generated baseline, show a short warning:

```text
The system will create a simple reproducible demo baseline. It is not an externally verified SOTA baseline.
```

For no baseline, show:

```text
The report will mark baseline comparison as unavailable or degraded.
```

Update `BaselineBoard` to display `baseline_intake` as the primary baseline status and move legacy `baseline_candidates` into a collapsed or deprecated section if still shown.

## Frontend Paper Reader

Update `LiteratureBoard` so clicking a paper selects it instead of only offering external links. Add a right-side `PaperReaderPanel` in the seismic workbench grid.

The reader displays:

- title
- authors, year, venue/source
- DOI, arXiv ID, source API
- abstract
- source link
- PDF link
- an iframe for `pdf_url` when present
- a fallback message when no PDF is available or the browser blocks display

The reader should not call browser-worker in this iteration. Keep the component boundary ready for a later `browserPreview` or `capture` prop.

## Report Provenance

Update `SystemProvenance.baseline_provenance` to prefer `baseline_intake`:

- baseline strategy
- source type
- trust level
- supplied or generated metrics
- limitations
- whether the comparison is demo-grade or research-grade

Reports must clearly distinguish:

- user-supplied baseline
- AI-generated demo baseline
- unavailable baseline
- system-executed experiment result
- unsupported or partial conclusions

## Error Handling

- Missing baseline selection defaults to `none` only if the frontend or older API client does not send a strategy. The UI should still require an explicit visible selection.
- Manual baseline invalid content returns `422`.
- Attaching baseline after start returns `409`.
- PDF iframe failure is handled in UI copy; it should not fail the run.
- Experiment redesign cap exhaustion is not a workflow failure; it becomes part of result interpretation and report limitations.

## Testing

Backend tests:

- baseline strategy schema validation and JSON round trip
- `POST /api/runs/{id}/baseline-intake` success for all three strategies
- baseline intake 404, 409, and 422 cases
- LangGraph path no longer includes automatic `baseline_discover` or `baseline_verify`
- classic path mirrors baseline intake behavior
- AI baseline path creates demo-grade provenance
- no-baseline path marks comparison degraded
- completed poor result routes to `experiment_redesign`
- redesign cap prevents infinite loops
- report provenance includes baseline strategy and limitations

Frontend tests or build-level checks:

- TypeScript types for baseline strategy and intake
- start flow attaches baseline intake before `startRun`
- manual baseline fields are included in payload
- LiteratureBoard selection drives PaperReaderPanel
- frontend production build passes

Verification:

- Run backend pytest.
- Run frontend build.
- If Docker CLI is available, optionally smoke-test compose; otherwise record Docker unavailability as a limitation.

## Migration and Compatibility

Existing runs without baseline strategy should deserialize successfully. The workflow should treat missing strategy as `none` or `ai_generated` only if explicitly configured later. For this change, use `none` as the safe compatibility default because it avoids silently inventing baseline evidence.

Legacy baseline discovery files and tests can remain temporarily. Any UI copy or docs must describe them as deprecated/manual debug capabilities if exposed.

## Open Follow-up

The later browser-worker reader enhancement can add:

- HTML capture
- screenshot preview
- downloaded PDF artifact display
- stored paper chunks beside the selected paper

That enhancement is intentionally out of scope for this implementation.
