# TrustSci-Agent Development Roadmap v2

更新时间：2026-06-04

本路线图基于 `PRD_v2.md`、`external_repository_reference.md`、`docs/REFERENCE_PROJECT_ANALYSIS.md`，以及此前用 CodeGraph / 代码结构阅读过的 AutoResearchClaw、PaperQA2、GPT Researcher、STORM、AI-Scientist、Agent Laboratory、scientific-agent-skills 等参考项目整理。

核心判断：

> TrustSci-Agent 不应 fork 某个外部项目，而应保持自研主系统，吸收 AutoResearchClaw 的可信引用链、PaperQA2 的论文级证据模型、STORM 的多视角规划、GPT Researcher 的工程化调研流程、AI-Scientist/AIDE 的实验迭代思想。

## 1. 当前状态

### 已完成

- 私有 GitHub 仓库与日常 pull / push 工作流。
- Docker Compose 开发环境，兼容 Linux / WSL。
- FastAPI backend。
- Next.js research workbench。
- 百炼 Qwen client。
- Provider-neutral LLM interface。
- LLM prompt / response / model / token / 时间日志。
- Planner Agent。
- Report Writer mock。
- Materials Project / Matbench 风格数据 profile。
- 小型 baseline result card。
- OpenAlex client。
- Crossref client。
- Semantic Scholar client，前端可选启用。
- arXiv client。
- LiteratureRouter：OpenAlex / Semantic Scholar / arXiv 统一检索。
- CitationVerifier：arXiv ID、Crossref DOI、DataCite DOI、OpenAlex title、Semantic Scholar title、arXiv title 多层核验。
- Evidence Ledger v2：记录 verification method、confidence、matched source、report eligibility。
- 前端展示 citation status、verification method、integrity score。
- Markdown / JSON report export。

### 当前缺口

- PDF 下载后的正文解析还没有接入 Evidence Ledger。
- Evidence Ledger 仍主要基于论文摘要，不是 page-level evidence。
- Claim Verifier 尚未实现，报告中的 claim 还没有逐条反查证据。
- Planner 还不是 STORM-style multi-perspective planner。
- Hypothesis Arena 仍是轻量 mock，没有多 reviewer 角色辩论。
- 缺少持久化 run workspace。
- 前端缺少 human gate：冻结引用、接受/拒绝证据、选择补搜方向。
- 参赛 demo case 需要封版，高质量案例和截图材料还未冻结。

## 2. 总体阶段

| 阶段 | 名称 | 优先级 | 目标 |
| --- | --- | --- | --- |
| Phase 0 | 已完成基础能力 | Done | 系统能从 question 跑到报告，并且不编造 References |
| Phase 1 | Evidence Core Hardening | P0 | 把“可信证据链”打磨成核心展示能力 |
| Phase 2 | Planner and Literature Intelligence | P0 | 提升问题拆解、检索策略、文献事实抽取质量 |
| Phase 3 | Human-in-the-loop Workspace | P1 | 让系统从一次性生成变成可审计科研工作台 |
| Phase 4 | Scientific Data and Experiment Layer | P1 | 强化 Materials / Matbench 数据与实验结果卡 |
| Phase 5 | Hypothesis Arena | P1 | 多智能体 reviewer 评审、修订、选择假设 |
| Phase 6 | Submission Freeze | P0 | 封版 demo、技术方案 PDF、视频脚本、可复现材料 |
| Phase 7 | Post-MVP Expansion | P2 | PDF RAG、KG、skill registry、tree search、领域包 |

## 3. Phase 1: Evidence Core Hardening

参考项目：

- AutoResearchClaw: citation verification、audit log、quality gate。
- PaperQA2: Doc / Text / metadata / citation-grounded answer。
- STORM: source tracking before final writing。

目标：

> 把“引用是真的，证据可追溯，报告不编文献”做成系统最稳定、最容易演示的能力。

开发任务：

1. PDF Evidence 接入。
   - browser-worker 下载 PDF 后返回 file path。
   - 后端保存 `papers/` artifact。
   - `pdf_parser` 输出 page chunks。
   - Evidence Ledger 增加 `page`、`section`、`evidence_text`。

2. Claim Verifier v1。
   - 从 final report 中抽取关键 claim。
   - 每条 claim 匹配 evidence ledger。
   - claim 缺证据时标记 `unsupported`。
   - 报告中 unsupported claim 自动降级为 risk / limitation。

3. CitationVerifier 强化。
   - 增加 verification report endpoint。
   - 保存每次核验原始 metadata snapshot。
   - 对 suspicious / hallucinated 文献给出原因分类。
   - 增加 API rate-limit fallback 和 cache。

4. Evidence Board 前端升级。
   - 展示 evidence eligibility。
   - 展示 matched source link。
   - 展示 PDF page / abstract / metadata 来源类型。
   - 增加 verified / suspicious / unsupported 筛选。

验收标准：

- 任意报告的 References 只包含 `report_eligible=true` 的论文。
- Evidence Ledger 中每条 evidence 都有 `verification_method` 和 `eligible_for_report`。
- 至少 1 篇论文能绑定 PDF page evidence。
- Claim Verifier 能输出 claim audit summary。
- 前端能展示 citation integrity score 和 evidence eligibility。

建议实现顺序：

1. PDF chunk schema。
2. PDF parser to evidence。
3. Claim audit schema。
4. Claim Verifier mock。
5. Claim Verifier with Qwen。
6. Frontend claim/evidence audit panel。

## 4. Phase 2: Planner and Literature Intelligence

参考项目：

- STORM: perspective-guided question asking。
- GPT Researcher: planner / executor / publisher。
- AutoResearchClaw: literature cards、synthesis、research gaps。

目标：

> Planner 不只是生成关键词，而是生成多视角、有证据要求、有风险控制的调研计划。

开发任务：

1. Perspective Planner。
   - 领域专家视角。
   - 机器学习专家视角。
   - 实验科学家视角。
   - 审稿人视角。
   - 产业转化视角。

2. Literature Miner Agent。
   - 从 verified papers 中抽取 knowledge cards。
   - 字段包括 method、dataset、finding、limitation、transferability、claim candidates。
   - 不允许 Literature Miner 生成新 citation。

3. Search Query Expansion。
   - Planner 输出 primary query、mechanism query、dataset query、baseline query、negative query。
   - LiteratureRouter 分配不同来源。
   - Semantic Scholar 开关继续保持用户可控。

4. Report Outline Builder。
   - 写报告前先冻结 outline 和 citation set。
   - Report Writer 只能使用 frozen evidence。

验收标准：

- Planner 输出至少 4 个 perspectives。
- 每个 perspective 至少生成 1 个 sub-question 和 1 个 evidence requirement。
- Literature Miner 能生成 3 到 8 张 knowledge cards。
- Report Writer 不新增 citation。
- 报告结构能显示 evidence-driven outline。

## 5. Phase 3: Human-in-the-loop Workspace

参考项目：

- AI-Research-SKILLs: research-state.yaml、findings.md、research-log.md。
- DeepScientist: findings memory。
- AutoResearchClaw: human gate / co-pilot mode。

目标：

> 让 TrustSci-Agent 从“一次性生成器”变成可复盘、可中断、可人工介入的科研工作台。

开发任务：

1. Run Workspace。

```text
workspace/run_xxx/
  research-state.yaml
  research-log.md
  papers/
  evidence/
  hypotheses/
  experiments/
  reports/
  to_human/
```

2. 持久化存储。
   - MVP 可先用 JSON files。
   - 后续迁移 SQLite / PostgreSQL。
   - run artifacts 与 API run state 对齐。

3. Human Gates。
   - 选择候选假设。
   - 接受/拒绝 evidence。
   - 冻结 citation set。
   - 要求补搜某个 perspective。

4. 前端交互。
   - Evidence freeze button。
   - Hypothesis select/revise。
   - Citation approve/reject。
   - Export workspace bundle。

验收标准：

- 每个 run 都能生成 workspace 目录。
- 前端能显示当前 human gate。
- 用户选择假设后可重新生成实验计划和报告。
- 已冻结 evidence set 不会被 Report Writer 擅自扩展。

## 6. Phase 4: Scientific Data and Experiment Layer

参考项目：

- RD-Agent: research/development agent 分工。
- AI-Scientist: experiment / writeup / review stage。
- AIDE / AI-Scientist-v2: branch exploration 思想。
- AutoResearchClaw: experiment result model。

目标：

> 把“研究计划”推进到“可执行验证路径”，但不急于做完整自动科研闭环。

开发任务：

1. Materials Project adapter。
   - API key 配置。
   - 查询材料 summary。
   - 生成 data profile。
   - 保存 query log。

2. Matbench baseline runner。
   - 至少 1 个轻量 task。
   - baseline result card 包含 train/test、metric、artifact path。
   - 区分 real result 和 expected result。

3. Experiment Designer v2。
   - 数据集选择理由。
   - baseline rationale。
   - metrics rationale。
   - ablation plan。
   - failure modes。

4. Result Card v2。
   - primary metric。
   - baseline comparison。
   - reproducibility notes。
   - limitations。

验收标准：

- 前端能展示真实 data profile。
- 至少一个 baseline result card 可复现。
- 报告中的 Results 明确区分 actual baseline result 与 expected outcome。
- 实验计划能被专家判断为可执行。

## 7. Phase 5: Hypothesis Arena

参考项目：

- AutoResearchClaw: multi-agent debate、reviewer gate。
- Agent Laboratory: professor / postdoc / engineer / reviewer roles。
- ChatReviewer: strengths / weaknesses / suggestions。
- Idea2Paper: anchored multi-agent review。

目标：

> 让假设生成不是单次 LLM 输出，而是经过多角色质疑、修订和选择。

开发任务：

1. Hypothesis Generator v2。
   - 每个假设必须绑定 supporting evidence ids。
   - 每个假设必须给出 novelty boundary。
   - 每个假设必须给出 measurable validation path。

2. Multi-reviewer Critic。
   - Literature Reviewer。
   - Domain Scientist。
   - ML/Experiment Reviewer。
   - Skeptical Reviewer。

3. Debate Log。
   - 记录 reviewer comments。
   - 记录 revision before / after。
   - 记录 selection rationale。

4. Novelty Check v1。
   - 用 verified literature 做 similar work search。
   - 标记 overlap risk。
   - 不做夸张 novelty claim。

验收标准：

- 至少生成 3 个假设。
- 每个假设至少有 2 条 evidence 支撑或明确说明证据不足。
- Critic scores 包含 novelty、feasibility、evidence support、reproducibility、competition fit。
- 被选中的假设有 revision history。

## 8. Phase 6: Submission Freeze

目标：

> 把系统打包成可评审、可演示、可复现的参赛作品。

开发任务：

1. Demo Case Freeze。
   - 固态电解质主题。
   - 固定输入问题。
   - 固定 run artifact。
   - 固定 final report。

2. 技术方案 PDF。
   - 控制在 20 页以内。
   - 系统架构。
   - agent workflow。
   - citation verification。
   - evidence ledger。
   - Qwen / 百炼调用日志。
   - demo result。

3. 演示视频脚本。
   - 输入 question。
   - Planner 输出。
   - 多源检索。
   - citation verification report。
   - evidence ledger。
   - hypothesis arena。
   - experiment plan。
   - final report export。

4. 代码可复现。
   - README 快速启动。
   - Docker Compose。
   - `.env.example`。
   - API docs。
   - test suite。

验收标准：

- 新机器 / WSL 能通过 Docker Compose 启动。
- demo run 能在 10 分钟内讲清楚。
- 报告中没有 hallucinated references。
- 百炼 Qwen 调用日志可截图。
- GitHub private repo 内容完整。

## 9. Phase 7: Post-MVP Expansion

这些能力有价值，但不应阻塞参赛 MVP：

- PaperQA2 级完整 PDF RAG。
- Local vector index / reranker。
- Evidence Graph / lightweight knowledge graph。
- Skill Registry。
- AI-Scientist-v2 / AIDE 式 experiment tree search。
- 多领域 domain packs。
- Zotero / Obsidian / Overleaf integrations。
- LangGraph workflow orchestration。
- MCP tool registry。

## 10. 近期推荐 Sprint

### Sprint A: PDF Evidence and Claim Audit

优先级：P0

交付：

- PDF chunk schema。
- PDF evidence ingestion。
- Claim audit schema。
- Claim Verifier mock。
- 前端 evidence details。

### Sprint B: Perspective Planner and Knowledge Cards

优先级：P0

交付：

- STORM-style perspectives。
- query expansion。
- Literature Miner Agent。
- knowledge cards。
- evidence-driven outline。

### Sprint C: Workspace and Human Gate

优先级：P1

交付：

- workspace/run_xxx。
- research-log.md。
- citation freeze。
- hypothesis select。
- report regenerate。

### Sprint D: Demo Freeze

优先级：P0

交付：

- 固态电解质 demo run。
- final report。
- screenshots。
- video script。
- submission checklist update。

## 11. 最小封版路径

如果时间紧，最低限度只做下面 6 件事：

1. PDF evidence 接入到 Evidence Ledger。
2. Claim Verifier mock + audit summary。
3. Perspective Planner。
4. Literature Miner knowledge cards。
5. Demo case freeze。
6. 技术方案 PDF + 10 分钟视频脚本。

这条路径能最大化比赛展示收益，因为它强化的是 TrustSci-Agent 与普通 deep research 最大的差异：可信引用、证据链、可验证科研假设。
