# TrustSci-Agent Roadmap

更新时间：2026-06-09

详细执行路线图见 [DEVELOPMENT_ROADMAP_V2.md](./DEVELOPMENT_ROADMAP_V2.md)。本文件作为团队快速入口，记录当前 MVP 的高层阶段和下一步优先级。

## Product Shape

TrustSci-Agent 不是 Reference Design 中 10 个外部参考模块的拼接，而是以 Evidence Engine 为中枢的科研假设生成流水线：

```text
Question
  -> Research Planner
  -> Literature & Data Acquisition
  -> Evidence Engine
  -> Hypothesis Arena
  -> Experiment Designer
  -> Report Generator
  -> Research Workspace
```

## Current Status

已完成 v1：

- FastAPI backend、Next.js workbench、Docker Compose。
- 百炼 Qwen client、统一 LLM interface、调用日志。
- Planner Agent 与 multi-perspective plan。
- OpenAlex / Crossref / Semantic Scholar / arXiv 多源检索。
- LiteratureRouter、CitationVerifier、Citation Audit Log。
- Evidence Ledger、PDF ingest、Browser Worker PDF 下载。
- Claim Verifier、Literature Miner、knowledge cards。
- Scientific data profile、小型 baseline result card。
- Hypothesis / Critic / Experiment Designer / Report Writer mock。
- Human Gate evidence accept/reject/freeze。
- Run Workspace artifacts。
- Markdown / JSON report export。

当前缺口：

- Hypothesis Arena 还缺多 reviewer debate、Revision Agent、novelty check。
- Claim Verifier 还缺 Qwen / embedding 语义核验。
- Citation Verifier 还缺 author/year match、metadata snapshot、cache、撤稿风险。
- 前端还缺独立 Literature Board、Claim Audit Panel、citation approve/reject、PDF export。
- Demo case、技术方案 PDF、视频脚本、截图材料还未封版。

## Phase Summary

| Phase | Name | Status | Priority |
| --- | --- | --- | --- |
| 0 | Project Scaffold | Done | P0 |
| 1 | Qwen Client + Planner | Done | P0 |
| 2 | Real Literature Retrieval | Done | P0 |
| 3 | Citation Verifier | Done v1 | P0 |
| 4 | PDF Evidence Ledger | Done v1 | P0 |
| 5 | Browser Worker | Done v1 | P1 |
| 6 | Gap Finder + Hypothesis Generator | Done v1 | P1 |
| 7 | Critic + Revision + Human Gate | In Progress | P1 |
| 8 | Experiment Designer | Done v1 | P1 |
| 9 | Final Report Generator | Done v1 | P0 |
| 10 | Demo Frontend | In Progress | P0 |
| 11 | Submission Package | Pending | P0 |

## Next Sprints

### Sprint C1: Hypothesis Arena Hardening

- Revision Agent。
- Multi-reviewer critic schema。
- Debate log。
- Hypothesis selection rationale。
- 选择假设后重建 experiment plan 和 report。

### Sprint C2: Evidence / Claim Audit UX

- 独立 Claim Audit Panel。
- Evidence Board 筛选。
- Citation approve/reject。
- Citation set freeze。
- Unsupported claim 降级策略。

### Sprint D: Demo Freeze

- 固态电解质 demo run。
- frozen evidence set。
- selected hypothesis。
- final report。
- Qwen logs。
- screenshots。
- video script。

## Minimum Freeze Path

如果时间紧，最低限度完成：

1. 固态电解质 demo case freeze。
2. Evidence set freeze，并确认 References 不超出 frozen set。
3. Hypothesis Arena 加 revision / debate 展示。
4. Claim Audit Panel。
5. Final report Markdown / JSON 样例。
6. 百炼 Qwen 调用日志截图。
7. 技术方案 PDF。
8. 10 分钟视频脚本和截图。
