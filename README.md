# TrustSci-Agent

TrustSci-Agent is a local-first Multi-Agent AI Scientist MVP for the 2026 contest topic "基于国产开源大模型的 AI Scientist 的研发与应用".

The first demo focuses on energy materials instead of a narrow seismic/geophysics label. The system is designed to generate a contest-format scientific hypothesis and research plan with verified references, evidence traceability, multi-agent critique, and an executable validation path.

## Why This Shape

- The contest requires Qwen/Bailian-based model usage, multi-agent or super-agent design, real references, and reproducible code.
- The PRD prioritizes a self-developed system over directly forking Hermes/OpenClaw.
- The reference repo `handsome-rich/Awesome-Auto-Research-Tools` is used as an ecosystem map. We borrow lifecycle patterns from AI-Scientist, Agent Laboratory, GPT Researcher, PaperQA2, OpenScholar, and AutoResearchClaw, while keeping our own architecture.

## Services

- `backend`: FastAPI workflow orchestrator.
- `frontend`: Next.js research workbench.
- `browser-worker`: Playwright webpage capture service with HTML, screenshot, and PDF-link download support.

## Run Locally

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Browser worker health: http://localhost:8010/health

Without `DASHSCOPE_API_KEY`, the system runs in deterministic demo mode. With a Bailian/Qwen-compatible key, the `QwenClient` calls the configured OpenAI-compatible endpoint.

## Docker Development

For day-to-day development on Linux or Windows WSL2:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Or use the Makefile:

```bash
make dev
```

The dev stack enables backend/browser-worker reload and Next.js polling-friendly file watching for WSL. Frontend dependencies and `.next` cache live in Docker named volumes so Windows filesystem performance does not pollute the repo.

Useful commands:

```bash
make down
make logs
make ps
make demo-candidates
make freeze-demo RUN_ID=run_xxx
make freeze-demo-strict RUN_ID=run_xxx
make freeze-demo-current RUN_ID=run_xxx
```

## Backend Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATA_DIR=../data uvicorn app.main:app --reload
```

Run a synchronous workflow from API docs or:

```bash
curl -X POST http://localhost:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"domain":"energy_materials","question":"Generate a verifiable solid-state electrolyte research hypothesis."}'
```

## API Flow

1. `POST /api/runs`
2. `POST /api/runs/{run_id}/start`
3. `GET /api/runs/{run_id}`
4. `GET /api/runs/{run_id}/evidence`
5. `GET /api/runs/{run_id}/hypotheses`
6. `GET /api/runs/{run_id}/report/export?format=md|json|pdf`
7. `GET /api/runs/{run_id}/workspace/export`
8. `POST /api/runs/{run_id}/workspace/restore`

See `docs/API.md` for the current FastAPI route surface.
See `docs/FRONTEND.md` for the current Next.js component structure.
See `docs/BAILIAN_QWEN.md` for Bailian/Qwen API configuration and ping checks.
See `docs/DEMO_FREEZE.md` for the fixed demo case freeze workflow.

## Current MVP Capabilities

- Planner Agent creates search queries and a workflow plan.
- OpenAlex retrieves real candidate papers.
- Crossref verifies DOI/title metadata.
- Evidence Ledger binds claims to source papers.
- Qwen/Bailian calls are logged to `data/outputs/llm_calls/{run_id}.jsonl`.
- Qwen/Bailian connectivity can be checked with `POST /api/system/qwen/ping`.
- Scientific Data Agent profiles Matbench metadata, an optional Materials Project adapter, and the bundled solid-electrolyte CSV.
- A deterministic baseline result card is written to `data/outputs/result_cards/`.
- Hypothesis Generator creates three candidate hypotheses.
- Final reports export as Markdown, JSON, and PDF.
- Run workspaces can be bundled and restored from disk snapshots.
- Demo runs can be frozen into `data/submission/{run_id}` with manifest, reports, workspace bundle, and Qwen logs.
- Critic Agent scores and revises hypotheses.
- Experiment Designer creates datasets, baselines, metrics, and failure modes.
- Report Writer exports contest fields and citation audit log.

## Important Privacy Note

This repository is connected to the private GitHub remote `git@github.com:maodousa/TrustSci-Agent.git`. See `docs/DEVELOPMENT_WORKFLOW.md` for the daily pull/test/push rhythm.
