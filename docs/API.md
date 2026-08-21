# FastAPI API Surface

> Current-code note (2026-08-21): use this file as the route index and Swagger as the runtime contract. The Chinese [runtime guide](onboarding/03_RUNTIME_FLOW.md), [input/output guide](onboarding/04_INPUT_OUTPUT.md), and [setup guide](onboarding/07_SETUP_GUIDE.md) explain how the routes fit together. Current route decorators and Pydantic schemas are authoritative.

Backend docs are available at:

```text
http://localhost:8000/docs
```

## System

- `GET /health`
- `GET /api/system/health`
- `GET /api/system/config`
- `POST /api/system/qwen/ping`

## Runs

- `POST /api/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/runs/{run_id}/experiment-assistance`
- `POST /api/runs/{run_id}/baseline-intake`
- `GET /api/runs/{run_id}/v3-summary`
- `POST /api/runs/{run_id}/start`
- `POST /api/runs/{run_id}/pause`
- `POST /api/runs/{run_id}/resume`
- `POST /api/runs/{run_id}/abandon`
- `POST /api/runs/{run_id}/run-sync`
- `POST /api/runs/{run_id}/continue`
- `POST /api/runs/{run_id}/steps/{step_name}/action`
- `POST /api/runs/{run_id}/recover`
- `GET /api/runs/workspaces`
- `GET /api/runs/{run_id}/papers`
- `POST /api/runs/{run_id}/papers/{paper_id}/decision`
- `POST /api/runs/{run_id}/papers/freeze`
- `POST /api/runs/{run_id}/papers/unfreeze`
- `GET /api/runs/{run_id}/evidence`
- `POST /api/runs/{run_id}/evidence/{evidence_id}/decision`
- `POST /api/runs/{run_id}/evidence/freeze`
- `POST /api/runs/{run_id}/evidence/unfreeze`
- `GET /api/runs/{run_id}/perspectives`
- `GET /api/runs/{run_id}/knowledge-cards`
- `GET /api/runs/{run_id}/paper-chunks`
- `GET /api/runs/{run_id}/claim-audit`
- `POST /api/runs/{run_id}/pdf-evidence`
- `GET /api/runs/{run_id}/data-profiles`
- `GET /api/runs/{run_id}/baseline-result`
- `GET /api/runs/{run_id}/hypotheses`
- `POST /api/runs/{run_id}/hypotheses/{hypothesis_id}/select`
- `POST /api/runs/{run_id}/baselines/discover`
- `POST /api/runs/{run_id}/baselines/{baseline_id}/verify-repo`
- `GET /api/runs/{run_id}/report`
- `POST /api/runs/{run_id}/report`
- `POST /api/runs/{run_id}/report/rebuild`
- `GET /api/runs/{run_id}/report/export?format=md`
- `GET /api/runs/{run_id}/report/export?format=json`
- `GET /api/runs/{run_id}/report/export?format=pdf`
- `GET /api/runs/{run_id}/workspace/export`
- `POST /api/runs/{run_id}/workspace/restore`
- `GET /api/runs/{run_id}/llm-calls`
- `GET /api/runs/{run_id}/artifacts`

## Data

- `GET /api/data/profiles`
- `POST /api/data/baseline`

## Browser

- `POST /api/browser/capture`
- `POST /api/browser/paper-preview`
- `GET /api/browser/artifacts/{filename}`

The browser endpoint proxies to `browser-worker`. In Docker, use the default `BROWSER_WORKER_URL=http://browser-worker:8010`. For local backend development outside Docker, set `BROWSER_WORKER_URL=http://localhost:8010`.

# Run resilience and paper preview

## Step action

`POST /api/runs/{run_id}/steps/{step_name}/action`

```json
{"action": "retry"}
```

`action` is `retry` or `skip`. The step must be in `waiting_action`. Skip is accepted only when the backend marks the step as `skippable`; critical baseline, experiment-result, and report steps cannot be silently skipped. The response is the updated `ResearchRun`.

## Explicit run recovery

`POST /api/runs/{run_id}/recover`

Recovery is initiated only after the user selects a historical task. A stale `running` step becomes `waiting_action`, completed steps remain unchanged, and `resume_count` plus `last_action` record the recovery. Completed runs return HTTP 409.

## Paper preview fallback

`POST /api/browser/paper-preview`

```json
{
  "paper_id": "paper_001",
  "source_url": "https://example.org/paper"
}
```

The response is either `web_snapshot` with a `screenshot_url`, or `metadata_only` with an `error_summary`. Successful snapshots are cached by paper ID and source URL. A snapshot is a reading aid and does not change citation verification or report eligibility.

`GET /api/browser/artifacts/{filename}` serves cached PNG screenshots from the shared browser-trace directory. Other file types and unsafe paths return HTTP 404.

Workflow steps retry transient network, rate-limit, model-service, and browser-service failures once. Deterministic validation errors do not receive a blind retry.
