# TrustSci-Agent Development Roadmap v2

更新时间：2026-06-09

本路线图基于 `PRD_v2.md`、`external_repository_reference.md`、`docs/REFERENCE_PROJECT_ANALYSIS.md`，以及此前用 CodeGraph / 代码结构阅读过的 AutoResearchClaw、PaperQA2、GPT Researcher、STORM、AI-Scientist、Agent Laboratory、scientific-agent-skills 等参考项目整理，并吸收最新讨论形成的产品判断：

> TrustSci-Agent 不应是 Reference Design 中 10 个模块的拼接，而应是以 Evidence Engine 为中枢、从 question 到可信科研报告的多智能体科研假设生成流水线。

## 1. 总体目标

MVP 需要支撑一条可演示、可审计、可复现的完整路径：

```text
Question
  -> Research Planner
  -> Literature & Data Acquisition
  -> Evidence Engine
  -> Hypothesis Arena
  -> Experiment Designer
  -> Report Generator
  -> Research Workspace
  -> Demo / Submission Materials
```

比赛展示重点：

1. 引用是真的。
2. 证据可追溯。
3. 假设可验证。
4. 多智能体过程可见。
5. 人在回路可控制。
6. 报告格式符合比赛要求。
7. 代码和 demo 可复现。

## 2. 当前状态

### 2.1 已完成

- 私有 GitHub 仓库与日常 pull / push 工作流。
- Docker Compose 开发环境，兼容 Linux / WSL。
- FastAPI backend。
- Next.js research workbench。
- 百炼 Qwen client。
- Provider-neutral LLM interface。
- LLM prompt / response / model / token / latency / 时间日志。
- Planner Agent。
- Report Writer mock。
- Materials Project / Matbench 风格 data profile。
- 小型 baseline result card。
- OpenAlex client。
- Crossref client。
- Semantic Scholar client，前端可选启用。
- arXiv client，前端可选启用。
- LiteratureRouter：OpenAlex / Semantic Scholar / arXiv 统一检索，其中 Semantic Scholar 和 arXiv 均由 run constraints 控制。
- CitationVerifier：arXiv ID、Crossref DOI、DataCite DOI、OpenAlex title、Semantic Scholar title、arXiv title 多层核验。
- Evidence Ledger v2：记录 verification method、confidence、matched source、report eligibility、human decision 和 frozen status。
- PDF chunk parser 与 run 级 PDF evidence ingest endpoint。
- Browser Worker：Playwright 截图、HTML snapshot、links 提取、PDF 下载。
- Claim Verifier v1：对 final report claims 进行 evidence ledger 反查并生成 claim audit。
- Perspective Planner v1：输出领域专家、ML/数据专家、实验专家、审稿人和应用视角问题。
- Literature Miner v1：从 evidence ledger 生成 knowledge cards。
- Run Workspace v1：每个 run 生成 research-state、research-log、结构化 artifacts 与 human checkpoints。
- 前端展示 citation status、verification method、integrity score。
- 前端支持将 browser-worker 下载的 PDF 入账为 Evidence。
- 前端展示 perspectives 与 knowledge cards。
- 前端展示 research workspace 路径和 artifact 清单。
- 前端 Claim Audit Panel 展示 claim support、weak、unsupported 明细。
- Evidence Board 支持 all / report / frozen / accepted / rejected / unsupported 筛选。
- CitationVerifier 面板支持接受/拒绝 citation、冻结/解冻 citation set。
- Human Gate v1：Evidence Board 支持接受/拒绝 evidence、冻结/解冻 evidence set。
- Report Writer / Claim Verifier 已遵守 frozen evidence set；References 由 frozen paper ids 约束。
- Markdown / JSON report export。

### 2.2 当前缺口

- PDF page-level evidence 已有 ingest 闭环，但尚未做到自动下载、自动匹配论文与自动入账。
- Claim Verifier v1 已实现确定性词汇匹配，仍需升级为 Qwen / embedding 辅助的语义核验。
- Citation Verifier 还需增强 author/year match、撤稿风险检查、原始 metadata snapshot、rate-limit fallback 和 cache。
- Planner 已有 STORM-style multi-perspective v1，但还没有多轮 simulated conversation 和按 perspective 的 query expansion。
- Literature Miner 已有 knowledge cards v1，但还没有 Qwen 抽取和完整 report outline freeze。
- Hypothesis Arena 已有 deterministic reviewer debate / revision v1，但还没有 Qwen 驱动的多轮辩论和 novelty checker。
- Run Workspace 已有文件化 v1，但还没有从 workspace 自动恢复内存态，也没有 workspace bundle。
- Human Gate 已有 evidence freeze 和 citation freeze v1；仍缺补搜方向选择、report outline freeze。
- 前端缺少独立 Literature Board、PDF export。
- 参赛 demo case、截图材料、技术方案 PDF、视频脚本尚未封版。

## 3. 阶段总览

| 阶段 | 名称 | 状态 | 优先级 | 目标 |
| --- | --- | --- | --- | --- |
| Phase 0 | 项目初始化 | Done | P0 | 工程骨架、Docker、FastAPI、Next.js、GitHub 协作 |
| Phase 1 | Qwen Client 与 Planner Agent | Done | P0 | 打通百炼 Qwen 与最小 Agent 调用闭环 |
| Phase 2 | 真实文献检索 | Done | P0 | OpenAlex / Crossref / Semantic Scholar / arXiv 多源真实论文 |
| Phase 3 | Citation Verifier | Done v1 | P0 | 多层反幻觉引用核验，References 不编造 |
| Phase 4 | PDF 解析与 Evidence Ledger | Done v1 | P0 | claim / evidence / paper 绑定和 page evidence 入账 |
| Phase 5 | Browser Worker | Done v1 | P1 | Playwright 网页采集、截图、PDF 下载 |
| Phase 6 | Gap Finder + Hypothesis Generator | Done v1 | P1 | 基于证据生成候选科学假设 |
| Phase 7 | Critic + Revision + Human Gate | In Progress | P1 | 多角色批判、修订、选择、冻结证据 |
| Phase 8 | Experiment Designer | Done v1 | P1 | 可验证实验计划与小型 result card |
| Phase 9 | Final Report Generator | Done v1 | P0 | 比赛字段报告、audit log、Markdown/JSON 导出 |
| Phase 10 | 前端演示版 | In Progress | P0 | 视频级工作台与固定 demo 路径 |
| Phase 11 | 参赛材料整理 | Pending | P0 | 技术方案、视频脚本、截图、提交清单 |
| Phase 12 | Post-MVP Expansion | Pending | P2 | PDF RAG、KG、skill registry、tree search、领域包 |

## 4. Phase 0：项目初始化

状态：已完成。

目标：搭建可运行的工程骨架。

已完成：

- Git 仓库和 private remote。
- backend / frontend / browser-worker / docs / data 目录。
- Docker Compose。
- FastAPI。
- Next.js。
- `.env.example`。
- README 初版。
- health / config / run mock API。
- 前端可提交 research question 并创建 run。

验收标准：

- `docker compose up` 可启动。
- 前端可访问。
- 后端 `/health` 正常。
- 前端提交问题后返回 `run_id`。

## 5. Phase 1：Qwen Client 与 Planner Agent

状态：已完成。

目标：打通百炼 Qwen API，完成最小 Agent 调用闭环。

已完成：

- `qwen_client.py`。
- 统一 LLM interface。
- prompt、response、model、token、latency、时间日志。
- Planner Agent。
- Planner 输出 `sub_questions`、`search_queries`、`workflow_plan`、`perspectives`。
- 前端展示基础 planner / timeline 输出。

后续增强：

- Prompt versioning。
- Planner 输出按 perspective 分配 query source。
- 失败重试和 prompt replay。

验收标准：

- 输入科研问题后，系统能生成研究计划。
- 所有模型调用有日志。
- 可以截图作为百炼 API 调用凭证。

## 6. Phase 2：真实文献检索

状态：已完成 v1。

目标：系统能检索真实论文，而不是依赖模型编造文献。

已完成：

- OpenAlex Client。
- Crossref Client。
- Semantic Scholar Client，可选。
- arXiv Client，可选。
- 统一 Paper schema。
- LiteratureRouter 聚合检索结果。
- DOI / arXiv ID / title 去重。
- 前端开关控制 Semantic Scholar 和 arXiv。

后续增强：

- 独立 Literature Board。
- Query expansion 按 perspective 分配来源。
- API cache、rate-limit fallback。
- 用户补搜方向。

验收标准：

- 输入关键词后返回真实论文候选。
- 每篇论文有 title、authors、year、doi/source_url。
- 前端可展示论文和来源。

## 7. Phase 3：Citation Verifier

状态：已完成 v1。

目标：建立反幻觉引用核验机制。

已完成：

- arXiv ID lookup。
- Crossref DOI verification。
- DataCite DOI fallback。
- OpenAlex title search。
- Semantic Scholar title search。
- arXiv title search。
- verified / suspicious / hallucinated / skipped 状态。
- citation verification report。
- citation audit log。
- Report Writer 只引用 verified 且 report eligible papers。

后续增强：

- author/year match。
- raw metadata snapshot。
- suspicious / hallucinated 原因分类。
- retraction risk。
- cache 与 rate-limit fallback。
- 前端 citation approve/reject。

验收标准：

- 每篇论文有验证状态、方法、confidence、matched source。
- DOI 或标题不匹配的论文不能进入 References。
- Report Writer 无法引用 hallucinated / rejected paper。
- 可以导出 citation audit log。

## 8. Phase 4：PDF 解析与 Evidence Ledger

状态：已完成 v1。

目标：让每个 claim 都能绑定证据。

已完成：

- PDF parser 输出 page chunks。
- run 级 PDF evidence ingest endpoint。
- Evidence Ledger 保存 claim、paper、source、page、section、verification method、eligible_for_report。
- Browser Worker 下载 PDF 后可入账 Evidence。
- 前端 Evidence Board 展示证据。

后续增强：

- 自动下载 PDF 并匹配 paper。
- 自动抽取 key findings、methods、limitations。
- page-level citation。
- Qwen/embedding evidence extraction。
- Evidence Board 筛选 verified / suspicious / unsupported。

验收标准：

- 至少一篇论文能绑定 PDF page evidence。
- 每条 evidence 有 source、page/section、verification method。
- Evidence Board 可展示来源和 eligibility。

## 9. Phase 5：Browser Worker

状态：已完成 v1。

目标：实现 Hermes 风格的浏览器资料采集能力。

已完成：

- browser-worker 服务。
- Playwright 打开网页。
- 保存 screenshot。
- 保存 HTML。
- 提取 links。
- 识别并下载 PDF。
- 前端 Browser Capture Panel。

后续增强：

- 浏览 trace 与 workspace 深度绑定。
- 自动把下载 PDF 匹配论文并入账。
- Browser capture 与 LiteratureRouter 互相补充。

验收标准：

- 输入论文 URL 后能保存网页快照。
- 能提取 PDF 链接。
- 能把下载 PDF 入账为 Evidence。

## 10. Phase 6：Gap Finder + Hypothesis Generator

状态：已完成 v1。

目标：基于证据生成候选科学假设。

已完成：

- Gap Finder mock。
- Hypothesis Generator mock。
- 每个假设包含 statement、rationale、supporting evidence、novelty claim、verification path。
- Critic mock 生成评分和 revision advice。

后续增强：

- Gap Finder 从 Literature Miner knowledge cards 真实抽取 gap。
- 每个假设至少绑定 2 条 evidence 或明确说明证据不足。
- Novelty boundary。
- Similar work search。

验收标准：

- 系统能生成多个候选假设。
- 每个假设有支撑证据或 weakly-supported 标记。
- 没有证据的假设不会被包装成已证明结论。

## 11. Phase 7：Critic Agent + Revision + Human Gate

状态：进行中。

目标：实现多智能体辩论和人在回路。

已完成：

- Critic Agent v1。
- Revision Agent v1。
- Multi-reviewer critic schema v1。
- Debate Log v1：reviewer comments、revision before / after、selection rationale。
- 用户选择假设接口。
- 用户选择假设后触发 experiment/report/claim audit rebuild。
- Human Gate v1：接受/拒绝 evidence。
- Human Gate v1：冻结/解冻 evidence set。
- Report Writer / Claim Verifier 遵守 frozen evidence。

下一步：

1. Qwen 驱动的多轮 reviewer debate。
2. Novelty Check v1：
   - 用 verified literature 做 similar work search。
   - 标记 overlap risk。
   - 不做夸张 novelty claim。
3. 引用接受/拒绝和 citation set freeze。

验收标准：

- 每个假设有 critic comments。
- 每个假设有 revised version。
- 用户可以选择最终假设。
- 被选中假设有 selection rationale。
- 前端 Hypothesis Arena 可完整展示 debate/revision。

## 12. Phase 8：Experiment Designer

状态：已完成 v1。

目标：生成可验证实验计划。

已完成：

- Experiment Designer mock。
- datasets、source、target、baselines、metrics、experiment steps、expected results、failure modes。
- Scientific Data Agent。
- Materials Project / Matbench 风格 profile。
- 小型 baseline result card。

后续增强：

- Materials Project adapter 真 API 查询。
- Matbench baseline runner。
- baseline rationale。
- metrics rationale。
- ablation plan。
- reproducibility notes。
- limitations。

验收标准：

- 选定假设后能生成完整实验计划。
- 实验计划可直接放入最终报告。
- Results 明确区分 actual baseline result 与 expected outcome。

## 13. Phase 9：Final Report Generator

状态：已完成 v1。

目标：输出比赛规范报告。

已完成：

- Final Report schema。
- Report Writer mock。
- Problem Statement、Rationale、Technical Details、Datasets、Methods、Experiments、Results、References。
- Citation Audit Log。
- Claim Audit Report。
- Markdown 导出。
- JSON 导出。
- Frozen evidence selector。

后续增强：

- Report Outline Builder。
- report outline freeze。
- unsupported claim 自动降级为 risk / limitation。
- PDF export。
- report quality checklist。

验收标准：

- Final Report 页面可展示完整报告。
- 可以导出 Markdown / JSON。
- 报告中没有 unverified references。
- References 不会超出 frozen evidence set。

## 14. Phase 10：前端演示版

状态：进行中。

目标：完成视频级前端。

已完成：

- Research Console。
- Run Timeline。
- Status Strip。
- Citation status panel。
- Perspective Plan Panel。
- Knowledge Cards Panel。
- Evidence Board。
- Human Gate evidence 操作。
- Hypothesis Arena。
- Experiment Plan。
- Browser Capture Panel。
- Workspace Panel。
- Report Viewer。

下一步：

1. 独立 Literature Board。
2. Claim / Evidence Audit Panel。
3. Hypothesis select 后的 rebuild feedback。
4. Report export UX。
5. Demo 数据固定入口。
6. 录屏路径打磨。
7. 移动/窄屏检查。

验收标准：

- 可以完整演示从输入问题到报告输出。
- 页面逻辑清晰。
- 可用于 10 分钟演示视频。
- 重点视图包括 Timeline、Literature Board、Evidence Board、Hypothesis Arena、Experiment Plan、Report。

## 15. Phase 11：参赛材料整理

状态：未开始。

目标：形成可提交作品。

任务：

1. Demo Case Freeze：
   - 固态电解质主题。
   - 固定输入问题。
   - 固定 run artifact。
   - 固定 final report。
2. 技术方案 PDF：
   - 控制在 20 页以内。
   - 系统架构。
   - agent workflow。
   - citation verification。
   - evidence ledger。
   - Qwen / 百炼调用日志。
   - demo result。
3. 演示视频脚本：
   - 输入 question。
   - Planner 输出。
   - 多源检索。
   - citation verification report。
   - evidence ledger。
   - hypothesis arena。
   - experiment plan。
   - final report export。
4. 代码可复现：
   - README 快速启动。
   - Docker Compose。
   - `.env.example`。
   - API docs。
   - test suite。
5. 截图与材料：
   - 百炼 API 调用截图。
   - 前端截图。
   - Citation Audit Log。
   - Claim Audit Report。
   - demo report。

验收标准：

- 新机器 / WSL 能通过 Docker Compose 启动。
- demo run 能在 10 分钟内讲清楚。
- 报告中没有 hallucinated references。
- 百炼 Qwen 调用日志可截图。
- GitHub private repo 内容完整。
- 技术方案不超过 20 页。

## 16. Phase 12：Post-MVP Expansion

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
- SQLite / PostgreSQL 持久化。
- Chroma / Qdrant 文献向量检索。

## 17. 近期推荐 Sprint

### Sprint C1：Hypothesis Arena Hardening

优先级：P0

交付：

- 已完成 v1：Revision Agent。
- 已完成 v1：Multi-reviewer critic schema。
- 已完成 v1：Debate log。
- 已完成 v1：Hypothesis selection rationale。
- 已完成 v1：选择假设后重建 experiment plan、report 和 claim audit。
- 已完成 v1：前端展示 revision / debate。
- 下一步：Qwen 驱动多轮 debate 与 novelty checker。

### Sprint C2：Evidence / Claim Audit UX

优先级：P0

交付：

- 已完成 v1：独立 Claim Audit Panel。
- 已完成 v1：Evidence Board verified / rejected / frozen / unsupported 筛选。
- 已完成 v1：Citation approve/reject。
- 已完成 v1：Citation set freeze。
- Unsupported claim 降级策略。

### Sprint D：Demo Freeze

优先级：P0

交付：

- 固态电解质 demo run。
- frozen evidence set。
- selected hypothesis。
- final report。
- Qwen logs。
- screenshots。
- video script。
- submission checklist update。

### Sprint E：Reproducibility Polish

优先级：P1

交付：

- Docker Compose smoke test。
- README 快速启动。
- API endpoint summary。
- workspace bundle export。
- local run restore from workspace。

## 18. 最小封版路径

如果时间紧，最低限度只做下面 8 件事：

1. 固态电解质 demo case freeze。
2. Evidence set freeze，并确认 References 不超出 frozen set。
3. Hypothesis Arena 加 revision / debate 展示。
4. Claim Audit Panel。
5. Final report Markdown / JSON 样例。
6. 百炼 Qwen 调用日志截图。
7. 技术方案 PDF。
8. 10 分钟视频脚本和截图。

这条路径最大化比赛展示收益，因为它强化的是 TrustSci-Agent 与普通 deep research 最大的差异：可信引用、证据链、多智能体批判、人在回路和可验证科研假设。

## 19. 开发风险与应对

### 风险 1：系统像普通 RAG

应对：演示 Multi-Agent Timeline、Hypothesis Arena、Critic Debate、Experiment Plan、Citation Audit Log 和 Evidence Board。

### 风险 2：引用幻觉

应对：Report Writer 禁止新增引用；References 只能从 verified papers 选择；unverified claim 标记为待验证；frozen evidence set 约束最终报告。

### 风险 3：科学问题太泛

应对：系统保持通用，demo 聚焦能源材料；固定高质量输入、run artifact 和 final report。

### 风险 4：工程范围过大

应对：优先视频级 MVP；不做微调、复杂 KG、大规模实验、多用户权限和全自动论文写作。

### 风险 5：前端拖慢进度

应对：聚焦 Timeline、Literature Board、Evidence Board、Hypothesis Arena、Experiment Plan、Report；其余保持简洁。

## 20. 最终提交物清单

1. 技术方案 PDF。
2. 源代码。
3. README。
4. `docker-compose.yml`。
5. `.env.example`。
6. demo 数据。
7. demo 输出报告。
8. Citation Audit Log。
9. Claim Audit Report。
10. 百炼 API 调用截图。
11. 前端截图。
12. 10 分钟内演示视频。
13. 参赛报名表及赛事要求材料。
