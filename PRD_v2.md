# TrustSci-Agent PRD v2

更新时间：2026-06-09

## 1. 一句话定位

TrustSci-Agent 是一个基于阿里云百炼 Qwen API 的可信多智能体 AI Scientist 系统，面向高价值科学问题，实现从科研问题输入、真实文献与开放数据采集、事实抽取、引用核验、证据链构建、科学假设生成、多智能体批判、人在回路、实验计划设计到标准化《科学假设与研究计划》输出的完整闭环。

项目不是普通 RAG，也不是论文自动写作工具，而是一个强调真实证据、可追溯引用、可验证假设和人机协作审计的科研智能体系统。

## 2. 版本定位

本版本在 PRD v1 与外部仓库参考分析的基础上，吸收最新产品讨论后重新收敛系统形态：

> TrustSci-Agent 不是 Reference Design 中 10 个参考模块的拼接，而是以 Evidence Engine 为中枢的科研假设生成流水线。

最终产品路径是：

```text
用户输入科研问题
  -> Research Planner 多视角拆题
  -> Literature & Data Acquisition 文献/数据采集
  -> Evidence Engine 事实抽取、引用核验、证据链
  -> Hypothesis Arena 假设生成、批判、修订、人在回路
  -> Experiment Designer 可验证实验计划生成
  -> Final Report Writer 输出比赛规范研究计划
  -> Research Workspace 保存全过程 artifacts
  -> 前端展示 Timeline / Literature Board / Evidence Board / Hypothesis Arena / Report
```

第一版参赛 MVP 以能源材料、固态电解质、催化剂发现作为主 demo，推荐主题为：

> 基于真实文献和开放材料数据，自动生成提升固态电解质离子电导率与稳定性的可验证科学假设。

## 3. 项目背景与目标

比赛要求参赛团队围绕特定学科领域，基于国产开源大模型 Qwen 系列，通过自研 Multi-Agent Systems 或超级智能体，实现从数据/文献输入到可验证科学假设输出的智能闭环。TrustSci-Agent 选择自研主系统，不直接套用 Hermes、OpenClaw 或其他通用 Agent 框架；Hermes、OpenClaw、CodeGraph、Awesome-Auto-Research-Tools 及其中项目作为开发工具和架构参考。

系统总目标：

1. 理解科研问题并生成多视角研究计划。
2. 检索真实文献与开放科学数据。
3. 校验 DOI、arXiv ID、标题、来源和引用真实性。
4. 抽取论文事实并构建 Evidence Ledger。
5. 识别研究缺口并生成候选科学假设。
6. 通过多智能体 reviewer / critic 进行批判、修订和选择。
7. 让用户在关键节点选择假设、接受或拒绝证据、冻结 evidence set。
8. 生成可验证实验计划、baseline result card 和标准化最终报告。
9. 导出 Citation Verification Report、Citation Audit Log、Markdown / JSON / PDF 报告和 workspace artifacts。

参赛目标：

1. 技术方案 PDF，不超过 20 页。
2. 源代码与 Docker Compose 可复现环境。
3. 上下文工程设计和多智能体架构说明。
4. 可交互前端页面。
5. 固定 demo case 与生成的《科学假设与研究计划》样例。
6. 百炼 Qwen API 调用日志、截图或凭证。
7. Citation Audit Log，用于证明参考文献没有虚构。
8. 10 分钟以内演示视频。

## 4. 项目不做什么

MVP 阶段明确不做：

1. 不做通用聊天机器人。
2. 不做全自动生成完整投稿论文。
3. 不把 Hermes / OpenClaw / AutoResearchClaw 直接作为系统主框架。
4. 不优先做模型微调。
5. 不做复杂多用户权限系统。
6. 不做大规模自动实验执行。
7. 不允许模型自由编造参考文献。
8. 不允许 Report Writer 阶段新增未验证引用。
9. 不追求一次性覆盖所有科学领域。
10. 不把地震、SeisLLM、EHS 作为当前主赛题标签。

## 5. 用户角色与核心诉求

主要用户：

1. 科研学生。
2. 科研导师。
3. AI for Science 研究者。
4. 比赛评委。
5. 需要快速生成 research proposal 的科研团队。

用户希望系统能够：

1. 不虚构文献。
2. 不只做文献总结。
3. 能提出有新意且可验证的科学假设。
4. 能说明假设依据和不确定性。
5. 能给出实验验证方案。
6. 能输出结构清晰的研究计划。
7. 能展示多智能体工作过程。
8. 能追溯每个关键结论的来源。

## 6. 核心用户故事

### 6.1 输入科研问题

用户输入：

> 我想研究固态电解质材料中离子电导率提升的潜在机制，请基于真实文献和开放数据库生成可验证科学假设。

系统输出：

- 子问题列表。
- 检索关键词。
- 多视角 perspectives。
- 计划调用的数据源。
- evidence requirements。
- 初始 workflow plan。

### 6.2 文献与数据采集

系统自动完成：

- 检索真实论文。
- 获取论文元数据。
- 校验 DOI、arXiv ID、标题、作者、年份。
- 解析 PDF 或网页。
- 抽取论文中的方法、数据集、结论、局限性。
- 识别 Materials Project / Matbench 风格数据源。
- 形成 Evidence Ledger。

### 6.3 候选假设生成

系统基于证据链生成多个候选假设。每个假设必须包含：

- hypothesis statement。
- rationale。
- supporting evidence ids。
- novelty claim。
- verification path。
- risk。
- required dataset。
- expected contribution。

### 6.4 智能体批判与修订

Critic / Reviewer Agent 对每个假设评价：

- novelty。
- self-consistency。
- feasibility。
- data availability。
- experimental clarity。
- risk of hallucination。
- overlap with existing work。
- scientific value。

Revision Agent 根据批评意见修改假设，要求保留支撑证据、删除夸张内容、降低不可验证表述、增强实验路径并标注不确定性。

### 6.5 人在回路

用户可以：

- 选择某个候选假设。
- 删除或拒绝不合理假设。
- 接受或拒绝 evidence。
- 冻结或解冻 evidence set。
- 补充领域约束。
- 要求系统重新辩论或降低假设风险。
- 要求系统加强实验设计。

### 6.6 最终报告生成

系统输出比赛规范格式的《科学假设与研究计划》：

- Problem Statement。
- Rationale。
- Technical Details。
- Datasets。
- Source。
- Target。
- Paper Title。
- Paper Abstract。
- Methods。
- Experiments。
- Results。
- References。
- Citation Verification Report。
- Citation Audit Log。
- Claim Audit Report。

## 7. 系统分层架构

```text
TrustSci-Agent
  Frontend Research Console
  Backend API Server
  Agent Orchestrator
  Literature & Data Acquisition Layer
  Evidence Engine
  Hypothesis Arena
  Experiment Designer
  Report Generator
  Research Workspace
```

### 7.1 Frontend Research Console

作用：提供可视化科研工作台。

核心页面：

- Research Console：输入研究问题、领域、检索数量、数据源开关。
- Run Timeline：展示多智能体执行过程。
- Literature Board / Citation Verifier：展示检索论文与核验状态。
- Evidence Board：展示证据链、接受/拒绝证据、冻结 evidence set。
- Hypothesis Arena：展示假设生成、批判、修改和选择。
- Experiment Plan：展示验证实验设计。
- Final Report：展示并导出最终报告。
- Workspace Panel：展示 run artifacts 和 human checkpoints。

### 7.2 Backend API Server

作用：负责前后端通信、任务管理、数据读写。

核心 API：

- `POST /api/runs` 创建研究任务。
- `POST /api/runs/{run_id}/start` 启动工作流。
- `GET /api/runs/{run_id}` 查询任务状态。
- `GET /api/runs/{run_id}/papers` 查询论文列表。
- `GET /api/runs/{run_id}/evidence` 查询证据链。
- `POST /api/runs/{run_id}/evidence/{evidence_id}/decision` 接受/拒绝证据。
- `POST /api/runs/{run_id}/evidence/freeze` 冻结 evidence set。
- `POST /api/runs/{run_id}/evidence/unfreeze` 解冻 evidence set。
- `GET /api/runs/{run_id}/hypotheses` 查询候选假设。
- `POST /api/runs/{run_id}/hypotheses/{hypothesis_id}/select` 选择假设。
- `POST /api/runs/{run_id}/report/rebuild` 基于当前 human gate 重建报告。
- `GET /api/runs/{run_id}/report/export` 导出报告。
- `GET /api/runs/workspaces` 查询可恢复 workspace snapshots。
- `GET /api/runs/{run_id}/workspace/export` 导出 workspace bundle。
- `POST /api/runs/{run_id}/workspace/restore` 从 workspace snapshot 恢复 run。

### 7.3 Agent Orchestrator

作用：调度所有 Agent 和工具。MVP 使用自研轻量状态机，不一开始引入复杂 orchestration 框架。

核心能力：

- 维护 workflow 状态。
- 管理 Agent 输入输出。
- 记录每一步中间结果。
- 控制工具调用。
- 支持失败记录与可恢复 artifacts。
- 支持人在回路暂停和继续。
- 生成 run-level research log。

### 7.4 Literature & Data Acquisition Layer

作用：获取真实资料。

包含：

- OpenAlex Client。
- Crossref Client。
- Semantic Scholar Client，可由前端启用。
- arXiv Client，可由前端启用。
- Browser Worker。
- PDF Downloader。
- PDF Parser。
- Dataset Profiler。
- Materials Project / Matbench 风格 adapter。

### 7.5 Evidence Engine

这是系统核心。作用：

- 校验引用。
- 抽取事实。
- 绑定 claim、evidence、paper、page、source。
- 判断 claim 是否有来源。
- 阻止虚构参考文献进入最终报告。
- 输出 Citation Verification Report、Citation Audit Log 和 Claim Audit Report。

Evidence Engine 包含：

- Citation Verifier。
- Claim Verifier。
- Evidence Ledger。
- Literature Miner。
- Paper Index。
- Audit Log Generator。
- Frozen Evidence Selector。

### 7.6 Hypothesis Arena

作用：生成、批判、迭代科学假设。

包含：

- Gap Finder Agent。
- Hypothesis Generator Agent。
- Critic Agent。
- Novelty Checker。
- Feasibility Judge。
- Revision Agent。
- Human Gate。

### 7.7 Experiment Designer

作用：把假设转成可验证实验计划。

输出：

- datasets。
- source。
- target。
- baselines。
- metrics。
- methods。
- ablation plan。
- experiment steps。
- expected results。
- failure modes。
- toy validation / baseline result card。

### 7.8 Report Generator

强约束：

- 只能使用 verified references。
- 只能使用 verified 且 report eligible 的 evidence。
- 如果 evidence set 已冻结，只能使用 `frozen_evidence_ids` 和 `frozen_paper_ids`。
- 不确定内容必须标注为待验证。
- 不允许新增未验证引用。
- 输出必须符合比赛字段。
- 附带 Citation Audit Log 和 Claim Audit Report。

### 7.9 Research Workspace

每个 run 生成一个 workspace：

```text
data/workspace/{run_id}/
  research-state.json
  research-log.md
  run.json
  papers/
  evidence/
  hypotheses/
  experiments/
  reports/
  to_human/
```

该结构用于调试、复现、演示视频和参赛材料整理，并支持导出为 workspace bundle，以及在服务重启后从 `run.json` 恢复 run。

## 8. Agent 与工具设计

### 8.1 Research Planner Agent

输入：用户研究问题、领域、约束条件、可用数据源。

输出：

- sub_questions。
- search_queries。
- databases。
- workflow_plan。
- evidence_requirements。
- risk_controls。
- perspectives。

perspectives 至少覆盖领域专家、机器学习专家、实验科学家、审稿人、产业转化和风险质疑视角。

### 8.2 Literature Search / Router

工具：

- OpenAlex。
- Crossref。
- Semantic Scholar。
- arXiv。
- Browser Worker。
- 用户上传 PDF。

候选论文按 DOI、arXiv ID、规范化标题去重，并按引用数、年份、标识符完整性排序。

### 8.3 Citation Verifier

校验维度：

- arXiv ID lookup。
- Crossref DOI verification。
- DataCite DOI fallback。
- OpenAlex title search。
- Semantic Scholar title search。
- arXiv title search。
- 后续扩展 author/year match、PDF 内容支持、撤稿风险。

状态：

```text
verified
suspicious
hallucinated
skipped
```

每篇论文输出 `verification_method`、`verification_confidence`、`matched_source`、`report_eligible`。

### 8.4 Literature Miner Agent

从 verified evidence 和 verified papers 中抽取：

- research problem。
- method。
- dataset。
- metric。
- experiment setting。
- key finding。
- limitation。
- future work。
- transferable idea。
- evidence ids。

Literature Miner 不允许生成新 citation。

### 8.5 Scientific Data Agent

MVP 功能：

- 读取 sample dataset。
- 输出字段描述。
- 输出任务类型。
- 输出数据可用性。
- 判断是否能支撑验证实验。
- 生成 Materials Project / Matbench 风格 profile。
- 生成小型 baseline result card。

后续功能：

- 接入 Materials Project API。
- 接入 Matbench task。
- 接入 Open Catalyst 或其他领域数据库。
- 支持用户上传 CSV。

### 8.6 Gap Finder / Hypothesis / Critic / Revision

Gap Finder 从论文事实、数据 profile、已有方法和局限性中输出 gap statement、supporting evidence、novelty opportunity 和 possible verification route。

Hypothesis Generator 每个假设必须绑定 supporting evidence ids、novelty boundary、verification path、risk、required dataset 和 expected contribution。

Critic Agent 模拟 reviewer 评分，Revision Agent 根据批评意见修改假设。后续升级为多 reviewer debate log。

### 8.7 Experiment Designer Agent

输出 datasets、source、target、baselines、metrics、methods、ablation、experiment steps、expected results、failure modes 和 result card。

### 8.8 Report Writer Agent

强制规则：

- References 只能来自 verified papers。
- 每个关键 claim 应绑定 evidence id。
- 不能添加未验证引用。
- 不确定结论必须标记为待验证。
- 输出格式必须满足比赛规范。

### 8.9 Tool / Skill Registry

可参考 Hermes skill loop、scientific-agent-skills 和 AI-Research-SKILLs。后续每个 skill 可包含：

```text
SKILL.md
input_schema.json
output_schema.json
examples/
tests/
failure_modes.md
```

第一批候选 skills：

- literature_search。
- citation_verify。
- pdf_parse。
- evidence_extract。
- hypothesis_debate。
- experiment_design。
- report_export。
- materials_data_profile。

## 9. 核心数据模型

### 9.1 ResearchRun

关键字段：

- `run_id`
- `domain`
- `question`
- `constraints`
- `status`
- `current_stage`
- `workspace_path`
- `workspace_artifacts`
- `plan`
- `perspectives`
- `papers`
- `citation_report`
- `paper_chunks`
- `evidence`
- `evidence_frozen`
- `frozen_evidence_ids`
- `frozen_paper_ids`
- `knowledge_cards`
- `claim_audit`
- `data_profiles`
- `baseline_result_card`
- `hypotheses`
- `experiment_plan`
- `report`
- `errors`

### 9.2 Paper

关键字段：

- `paper_id`
- `title`
- `authors`
- `year`
- `doi`
- `arxiv_id`
- `venue`
- `abstract`
- `source_api`
- `source_url`
- `pdf_url`
- `verification_status`
- `verification_method`
- `verification_confidence`
- `matched_source`
- `report_eligible`

### 9.3 EvidenceItem

```json
{
  "evidence_id": "ev_001",
  "paper_id": "paper_001",
  "claim": "...",
  "evidence_type": "paper | pdf_page | browser",
  "source_title": "...",
  "source_url": "...",
  "source_path": "...",
  "doi": "...",
  "page": 3,
  "section": "Methods",
  "quote_or_summary": "...",
  "confidence": 0.7,
  "verified": true,
  "verification_method": "openalex_title",
  "verification_confidence": 0.91,
  "matched_source": "https://openalex.org/...",
  "eligible_for_report": true,
  "human_decision": "pending | accepted | rejected",
  "human_note": "",
  "frozen": false
}
```

### 9.4 Hypothesis

关键字段：

- `hypothesis_id`
- `statement`
- `rationale`
- `supporting_evidence`
- `novelty_claim`
- `verification_path`
- `critic`
- `revised_statement`
- `selected`

### 9.5 ExperimentPlan

关键字段：

- `datasets`
- `source`
- `target`
- `baselines`
- `metrics`
- `experiment_steps`
- `expected_results`
- `failure_modes`

### 9.6 ResearchReport

必须覆盖：

- `problem_statement`
- `rationale`
- `technical_details`
- `datasets`
- `source`
- `target`
- `paper_title`
- `paper_abstract`
- `methods`
- `experiments`
- `results`
- `references`
- `citation_audit_log`

## 10. 前端设计

### 10.1 Research Console

- 输入研究问题。
- 选择领域。
- 设置检索论文数量。
- 启用或关闭 Semantic Scholar。
- 启用或关闭 arXiv。
- 启动任务。
- 刷新当前 run。

### 10.2 Run Timeline

展示 Planner、Literature Search、Citation Verification、Evidence Ledger、Literature Mining、Scientific Data Profile、Hypothesis Debate、Experiment Design、Report Writing、Claim Verification 等阶段。

### 10.3 Literature / Citation Board

展示论文标题、年份、DOI、source API、verification status、verification method、confidence、matched source、report eligibility。

### 10.4 Evidence Board

展示 claim、quote_or_summary、source paper、DOI、page、section、confidence、verified status、human decision、frozen status，并支持接受/拒绝 evidence 与冻结/解冻 evidence set。

### 10.5 Hypothesis Arena

展示 H1/H2/H3、支撑证据、novelty、feasibility、verifiability、critic comments、revised version 和 select button。

### 10.6 Experiment Plan

展示 datasets、source、target、baseline、metrics、methods、expected results、failure modes 和 result card。

### 10.7 Final Report

展示标准化研究计划、References、Citation Audit Log、Claim Audit Report，并支持 Markdown / JSON / PDF 导出。

## 11. 技术栈与仓库策略

Backend：

- Python。
- FastAPI。
- Pydantic。
- httpx。
- pypdf / PDF parser。
- reportlab / PDF report export。
- Playwright client / browser-worker。
- Docker。
- 后续可迁移 SQLite / PostgreSQL、Chroma / Qdrant。

Frontend：

- Next.js。
- React。
- TypeScript。
- CSS / 轻量设计系统。
- 后续可增加 React Query、Markdown renderer。

Model：

- 百炼 Qwen：主推理。
- Qwen Plus / Flash：批量低成本任务。
- 可选 embedding model：后续用于 claim/evidence semantic matching。
- 不优先微调。

开发策略：

- 主系统保持自研。
- 外部项目作为架构、工具和数据结构参考。
- 私有 GitHub 仓库协作开发。
- 每天开始前检查 remote 更新；开发完成后 commit / push。

## 12. 外部参考模块与系统映射

Reference Design 的 10 个模块不是最终系统模块，而是参考来源。

| 参考模块 | 主要参考项目 | 进入最终系统的位置 |
| --- | --- | --- |
| Literature Search | AutoResearchClaw / GPT Researcher | Literature & Data Acquisition |
| Citation Verifier | AutoResearchClaw / PaperQA2 | Evidence Engine |
| PDF RAG | PaperQA2 / OpenScholar | Literature Miner + Evidence Engine |
| Planner | STORM / GPT Researcher | Research Planner Agent |
| Evidence Ledger | PaperQA2 / Idea2Paper | Evidence Engine |
| Hypothesis Debate | AutoResearchClaw / Agent Laboratory | Hypothesis Arena |
| Novelty Check | Idea2Paper / AI-Scientist-v2 | Critic Agent / Novelty Checker |
| Experiment Design | RD-Agent / AIDE / AI-Scientist-v2 | Experiment Designer |
| Skill Registry | scientific-agent-skills / AI-Research-SKILLs | Tool & Skill Layer |
| Workspace Memory | AI-Research-SKILLs / DeepScientist | Research Workspace |

## 13. MVP 验收标准

输入科研问题后，MVP 必须满足：

1. Planner Agent 生成 `search_queries`、`sub_questions`、`workflow_plan`、`perspectives`、`evidence_requirements`。
2. LiteratureRouter 返回真实论文候选，而不是模型编造论文。
3. 默认支持 OpenAlex，Semantic Scholar 与 arXiv 可由前端开关启用。
4. CitationVerifier 生成结构化 `citation_report`。
5. 每篇论文包含 `verification_method`、`verification_confidence`、`matched_source`、`report_eligible`。
6. Evidence Ledger 每条证据包含 `verification_method`、`eligible_for_report`、`human_decision`。
7. LiteratureMiner 输出 knowledge cards，且每张卡绑定 evidence ids。
8. Hypothesis Agent 输出多个候选假设，每个假设绑定 supporting evidence 或明确说明证据不足。
9. Critic Agent 输出 novelty、self-consistency、verifiability、data availability、risk、revision advice。
10. Human Gate 支持选择假设、接受/拒绝 evidence、冻结/解冻 evidence set。
11. Report Writer 只把 verified 且 report eligible 的论文放入 References。
12. 冻结 evidence set 后，Report Writer 不会引用 frozen set 之外的证据或论文。
13. Final report 覆盖比赛字段并导出 Markdown 和 JSON。
14. 前端展示 timeline、citation status、verification method、integrity score、evidence board、perspectives、knowledge cards、hypothesis arena、experiment plan、report 和 workspace artifacts。
15. LLM 调用记录 prompt、response、model、token、latency 和时间。
16. 测试覆盖 Qwen client、planner、literature clients、literature router、citation verifier、evidence freeze、claim verifier、report writer 和 workflow。

## 14. 当前已落地能力

- Docker Compose 开发环境，兼容 Linux / WSL。
- FastAPI backend。
- Next.js research workbench。
- 百炼 Qwen client 与 provider-neutral LLM interface。
- LLM prompt / response / model / token / 时间日志。
- Planner Agent 与 multi-perspective plan。
- OpenAlex / Crossref / Semantic Scholar / arXiv 客户端。
- LiteratureRouter 多源统一检索与去重。
- 前端 Literature Board 展示检索来源、论文元数据、source/pdf 链接和核验状态。
- CitationVerifier 多层核验。
- Evidence Ledger v2。
- PDF chunk parser 与 run 级 PDF evidence ingest。
- Browser worker 截图 / HTML / PDF 下载。
- Claim Verifier v1 与 Claim Audit Report。
- 前端 Claim Audit Panel 与 claim support/weak/unsupported 明细展示。
- Evidence Board 支持 all/report/frozen/accepted/rejected/unsupported 筛选。
- CitationVerifier 面板支持接受/拒绝 citation、冻结/解冻 citation set。
- Literature Miner v1 与 knowledge cards。
- Materials Project / Matbench 风格 data profile。
- 小型 baseline result card。
- Hypothesis / Critic / Revision / Experiment Designer v1。
- Multi-reviewer debate log、revision history、selection rationale。
- 用户选择假设后自动重建 experiment plan、report 和 claim audit。
- Human Gate v1：接受/拒绝 evidence、冻结/解冻 evidence set。
- Report Writer mock，遵守 verified references 与 frozen evidence set。
- Run Workspace v1。
- Workspace bundle export v1。
- Workspace restore v1。
- Markdown / JSON / PDF report export。

## 15. 当前缺口

- PDF page-level evidence 已有 ingest 闭环，但尚未做到自动下载、自动匹配论文与自动入账。
- Claim Verifier v1 仍是确定性词汇匹配，需升级为 Qwen / embedding 语义核验。
- Citation Verifier 还需增加 author/year match、撤稿风险、原始 metadata snapshot 和 cache。
- Literature Miner 已有 knowledge cards v1，但还没有 Qwen 抽取和完整 report outline freeze。
- Hypothesis Arena 已有 deterministic reviewer debate / revision v1，但还没有 Qwen 驱动的多轮辩论和 novelty checker。
- Run Workspace 已有文件化、bundle export 和手动 restore v1；后续可增强为启动时自动恢复。
- 前端缺少补搜方向。
- Demo case、截图、视频脚本和 20 页技术方案尚未封版。

## 16. 暂不纳入 MVP 的能力

- 完整 PaperQA2 级 PDF RAG。
- 大规模向量库和 page-level citation。
- AI-Scientist-v2 式 tree search。
- 自动代码生成和大规模沙盒实验。
- 直接 fork 外部项目作为主系统。
- 自动生成完整论文投稿稿。
- 多用户系统。
- 模型微调。

## 17. 关键创新点

### 17.1 可信证据链

每个科学结论都绑定 evidence，不允许无来源 claim 进入最终报告。

### 17.2 反幻觉引用核验

References 只能来自 verified papers，通过 DOI、arXiv ID、title、source 等多层校验，并输出 Citation Audit Log。

### 17.3 多智能体假设辩论

系统不是单 Agent 生成答案，而是 Planner、Literature Miner、Gap Finder、Hypothesis Generator、Critic、Revision、Human Gate 协同。

### 17.4 可验证实验设计

每个假设必须转化为 dataset、baseline、metric、method、expected result 和 failure modes。

### 17.5 科研工作区持久化

每次 run 保存 research-state、evidence、hypotheses、experiments、report、claim audit 和 human checkpoints，支持复现和审计。

## 18. 主要风险与应对

### 风险 1：系统像普通 RAG

应对：突出 Multi-Agent Timeline、Hypothesis Arena、Critic 辩论、Experiment Plan、Citation Audit Log 和 Evidence Board。

### 风险 2：引用幻觉

应对：Report Writer 禁止新增引用；References 只能从 verified papers 选择；unverified claim 标记为待验证；冻结 evidence set 后报告不能扩展证据。

### 风险 3：科学问题太泛

应对：系统保持通用，但 demo 聚焦能源材料和固态电解质；固定一个高质量案例，不现场随机跑完整流程。

### 风险 4：工程范围过大

应对：先完成 MVP；不做微调、复杂 KG、大规模实验、多用户权限和全自动论文写作。

### 风险 5：前端拖慢进度

应对：优先完成视频级工作台，重点展示 Timeline、Literature Board、Evidence Board、Hypothesis Arena、Experiment Plan 和 Report。

## 19. 最终提交物清单

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

## 20. 当前版本结论

TrustSci-Agent 的最终形态是一个证据链驱动的多智能体科研假设生成系统。Reference Design 中的 10 个模块只是外部参考仓库的能力来源；PRD 中的 TrustSci-Agent 才是最终产品长相。

最终系统应收敛为：

1. Research Planner。
2. Literature & Data Acquisition。
3. Evidence Engine。
4. Hypothesis Arena。
5. Experiment Designer。
6. Report Generator。
7. Frontend Research Console。
8. Research Workspace。

这套结构既能覆盖比赛要求的文献挖掘、事实提取、逻辑假设生成、多轮迭代、人在回路，也能突出技术深度、科学价值和应用潜力。
