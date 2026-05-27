# TrustSci-Agent Architecture

TrustSci-Agent is a Qwen-compatible multi-agent AI Scientist MVP. It is optimized for the contest requirement: generate a standardized, verifiable scientific hypothesis and research plan from literature/data inputs.

## Runtime Services

- `frontend`: Next.js research workbench.
- `backend`: FastAPI agent orchestrator and APIs.
- `browser-worker`: lightweight webpage capture service inspired by Hermes-style browser tooling.

## Agent Flow

```text
Research Question
  -> Planner Agent
  -> Literature Search Tool
  -> Citation Verifier Agent
  -> Evidence Ledger
  -> Gap Finder Agent
  -> Hypothesis Generator Agent
  -> Critic Agent
  -> Experiment Designer Agent
  -> Report Writer Agent
```

## Trust Controls

- The report writer receives only papers already present in the run state.
- Crossref verification checks DOI and title similarity.
- The evidence ledger binds each claim to a paper and verification state.
- The final report includes a citation audit log.
- The system runs without an LLM key in deterministic demo mode, but can call Bailian/Qwen through an OpenAI-compatible endpoint when configured.

## First Demo Domain

The initial demo domain is energy materials, especially solid-state electrolyte hypothesis generation. This follows the PRD direction of avoiding a narrow seismic/geophysics label while still presenting a high-value AI for Science scenario with public datasets and measurable validation paths.

