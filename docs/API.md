# FastAPI API Surface

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
- `POST /api/runs/{run_id}/start`
- `POST /api/runs/{run_id}/run-sync`
- `GET /api/runs/workspaces`
- `GET /api/runs/{run_id}/papers`
- `GET /api/runs/{run_id}/evidence`
- `POST /api/runs/{run_id}/evidence/{evidence_id}/decision`
- `POST /api/runs/{run_id}/evidence/freeze`
- `POST /api/runs/{run_id}/evidence/unfreeze`
- `GET /api/runs/{run_id}/data-profiles`
- `GET /api/runs/{run_id}/baseline-result`
- `GET /api/runs/{run_id}/hypotheses`
- `POST /api/runs/{run_id}/hypotheses/{hypothesis_id}/select`
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

The browser endpoint proxies to `browser-worker`. In Docker, use the default `BROWSER_WORKER_URL=http://browser-worker:8010`. For local backend development outside Docker, set `BROWSER_WORKER_URL=http://localhost:8010`.
