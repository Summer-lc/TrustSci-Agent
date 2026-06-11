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

```bash
make freeze-demo RUN_ID=run_xxx
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

## Submission Use

- `manifest.json` is the authoritative demo artifact index.
- `README.md` is the human-readable freeze summary.
- `reports/` provides final report samples for reviewers and screenshots.
- `{run_id}-workspace.zip` proves the research state can be reproduced.
- `logs/{run_id}.jsonl` is the source for Bailian/Qwen call screenshots.
