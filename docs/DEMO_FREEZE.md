# Demo Case Freeze

Use this workflow when a run is ready to become the fixed contest demo case.

## Recommended Demo Question

```text
请围绕固态电解质材料的离子电导率与稳定性提升，基于真实文献和开放数据库，生成可验证科学假设与实验计划。
```

## Human Gate Before Freeze

- Review the Literature Board and reject out-of-scope or weak citations.
- Freeze the citation set.
- Review the Evidence Board and reject weak or unsupported evidence.
- Freeze the evidence set.
- Select one hypothesis in Hypothesis Arena.
- Rebuild the report and inspect Claim Audit.
- Export Markdown / JSON / PDF report once.

## Freeze Command

List candidate runs and their readiness checks:

```bash
make demo-candidates
```

Create a draft package, allowing warnings:

```bash
make freeze-demo RUN_ID=run_xxx
```

Create a final package and fail if evidence/citations/report/logs/claim audit are not ready:

```bash
make freeze-demo-strict RUN_ID=run_xxx
```

If the current verified and non-rejected citations/evidence have already been reviewed and should become the fixed demo set, freeze them and create the strict package in one command:

```bash
make freeze-demo-current RUN_ID=run_xxx
```

The command creates:

```text
data/submission/{run_id}/
  manifest.json
  README.md
  reports/{run_id}.md
  reports/{run_id}.json
  reports/{run_id}.pdf
  {run_id}-workspace.zip
  logs/{run_id}.jsonl
```

If Qwen/Bailian logging is not available, the manifest keeps the freeze package usable but records a warning.
For final contest packaging, prefer `make freeze-demo-strict` after manual frontend review. It fails if Claim Audit still has unsupported claims. Use `make freeze-demo-current` only when the current verified set is accepted as the fixed demo evidence set.

## Current Local Demo Freeze

Current local frozen candidate:

- Run id: `run_6ed0df4301`
- Package: `data/submission/run_6ed0df4301`
- Papers: 2 verified references
- Evidence: 2 frozen evidence items
- Citation integrity score: 1.0
- Claim support score: 0.929
- Strict warnings: none

`data/submission/` is intentionally git-ignored. Keep the package locally for screenshots, video recording, and final submission assembly.

## Submission Use

- `manifest.json` is the authoritative demo artifact index.
- `README.md` is the human-readable freeze summary.
- `reports/` provides final report samples for reviewers and screenshots.
- `{run_id}-workspace.zip` proves the research state can be reproduced.
- `logs/{run_id}.jsonl` is the source for Bailian/Qwen call screenshots.
