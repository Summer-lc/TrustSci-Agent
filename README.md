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
6. `GET /api/runs/{run_id}/report/export`

## Current MVP Capabilities

- Planner Agent creates search queries and a workflow plan.
- OpenAlex retrieves real candidate papers.
- Crossref verifies DOI/title metadata.
- Evidence Ledger binds claims to source papers.
- Qwen/Bailian calls are logged to `data/outputs/llm_calls/{run_id}.jsonl`.
- Scientific Data Agent profiles Matbench metadata, an optional Materials Project adapter, and the bundled solid-electrolyte CSV.
- A deterministic baseline result card is written to `data/outputs/result_cards/`.
- Hypothesis Generator creates three candidate hypotheses.
- Critic Agent scores and revises hypotheses.
- Experiment Designer creates datasets, baselines, metrics, and failure modes.
- Report Writer exports contest fields and citation audit log.

## Important Privacy Note

This repository is initialized locally only. No GitHub remote is configured by default, so it remains visible only on this machine unless you explicitly add a private remote later. See `docs/GITHUB_PRIVATE_REPO.md` for private repo creation and collaborator invitation commands.
