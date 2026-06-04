# TrustSci-Agent PRD v2

## 1. 版本定位

本版本在 PRD v1 的基础上，根据 `external_repository_reference.md` 对 AutoResearchClaw、PaperQA2、GPT Researcher、STORM 等项目的分析，重新收敛系统重点：

> TrustSci-Agent 不是从 idea 到 paper 的自动论文系统，而是从 question 到可信科研报告的多智能体系统。

核心竞争力从“能生成研究计划”升级为：

> 多源真实文献检索 + 多层 citation verification + evidence ledger + 多智能体假设评审 + 可执行实验计划。

第一版参赛 MVP 仍以能源材料/固态电解质作为主 demo。

## 2. 更新原因

外部仓库分析显示，AutoResearchClaw 与比赛任务最接近，但它面向 idea-to-paper；我们的任务应保持 question-to-report。它最值得吸收的不是论文写作链，而是：

- OpenAlex / Semantic Scholar / arXiv 多源文献检索，其中 Semantic Scholar 和 arXiv 均可在前端配置区按需启用。
- DOI / arXiv ID / title 多层引用核验。
- 不允许虚构引用进入 References。
- Citation audit log 和 verification report。
- 多智能体 critic / reviewer gate。

PaperQA2 的价值在于论文级 RAG 和 page-level evidence，但依赖较重，MVP 阶段先吸收数据结构和证据绑定思想，不直接引入完整库。

## 3. 产品目标

用户输入一个科研问题后，系统应输出一份可审计科研报告：

```text
Question
Planner sub-questions
Search queries
Verified literature
Evidence ledger
Candidate hypotheses
Critic scores
Experiment plan
Baseline result card
Final report
Citation verification report
Citation audit log
```

报告中的 References 只能来自 verified papers。Suspicious、hallucinated、skipped 文献只能进入 audit log，不能进入正式 References。

## 4. 核心用户故事

### 4.1 科研问题规划

用户输入：

> 基于近年文献和开放材料数据库，生成提升固态电解质离子电导率与稳定性的可验证科学假设。

系统输出：

- `sub_questions`
- `search_queries`
- `perspectives`
- `workflow_plan`
- `evidence_requirements`
- `risk_controls`

### 4.2 真实文献检索

系统通过 `LiteratureRouter` 同时整合：

- OpenAlex
- arXiv（前端可选启用）
- Semantic Scholar（前端可选启用）

候选论文按 DOI、arXiv ID、规范化标题去重，并按引用数、年份、标识符完整性排序。

### 4.3 多层引用核验

系统通过 `CitationVerifier` 进行多层校验：

1. arXiv ID lookup
2. Crossref DOI verification
3. DataCite DOI fallback
4. OpenAlex title search
5. Semantic Scholar title search
6. arXiv title search

每篇论文输出：

```json
{
  "verification_status": "verified | suspicious | hallucinated | skipped",
  "verification_method": "crossref_doi",
  "verification_confidence": 0.95,
  "matched_source": "https://doi.org/...",
  "report_eligible": true
}
```

### 4.4 Evidence Ledger v2

每条证据必须绑定文献核验信息：

```json
{
  "claim": "...",
  "paper_id": "...",
  "doi": "...",
  "quote_or_summary": "...",
  "verified": true,
  "verification_method": "openalex_title",
  "verification_confidence": 0.91,
  "matched_source": "https://openalex.org/...",
  "eligible_for_report": true
}
```

### 4.5 假设生成与评审

在假设生成前，系统会从 verified evidence 生成 Literature Knowledge Cards：

- finding
- method
- dataset
- limitation
- transferability
- evidence ids
- report eligibility

系统生成多个候选假设，并由 Critic Agent 评分：

- novelty
- self-consistency
- verifiability
- data availability
- risk
- revision advice

最终报告只能使用 evidence ledger 中 `eligible_for_report=true` 的证据作为强支撑。

### 4.6 实验计划与结果卡

系统输出：

- datasets
- source / target
- baselines
- metrics
- experiment steps
- expected results
- failure modes
- baseline result card

MVP 只要求小型可执行 baseline result card，不承诺完整自动实验闭环。

## 5. 系统模块

```text
ResearchConsole
  -> PlannerAgent
  -> LiteratureRouter
       -> OpenAlexClient
       -> SemanticScholarClient
       -> ArxivClient
  -> CitationVerifier
       -> arXiv ID
       -> Crossref DOI
       -> DataCite DOI
       -> OpenAlex title
       -> Semantic Scholar title
       -> arXiv title
  -> EvidenceLedger
  -> LiteratureMinerAgent
  -> ScientificDataAgent
  -> HypothesisAgent
  -> CriticAgent
  -> ExperimentDesignerAgent
  -> ReportWriterAgent
```

## 6. MVP 验收标准

输入科研问题后，系统必须满足：

1. Planner Agent 生成 `search_queries`、`sub_questions`、`workflow_plan`。
2. LiteratureRouter 返回真实论文候选，而不是模型编造论文。
3. 默认支持 OpenAlex，Semantic Scholar 与 arXiv 可由前端开关启用。
4. CitationVerifier 生成结构化 `citation_report`。
5. 每篇论文包含 `verification_method`、`verification_confidence`、`matched_source`、`report_eligible`。
6. Evidence Ledger 每条证据包含 `eligible_for_report`。
7. Planner 输出多视角 `perspectives`，覆盖领域专家、ML/数据专家、实验专家、审稿人和应用视角。
8. LiteratureMiner 输出 knowledge cards，且每张卡绑定 evidence ids。
9. Report Writer 只把 verified 且 report eligible 的论文放入 References。
10. Final report 导出 Markdown 和 JSON。
11. 前端展示 citation status、verification method、integrity score、perspectives 和 knowledge cards。
12. 测试覆盖 arXiv client、literature router、citation verifier、planner perspectives、knowledge cards、workflow。

## 7. 暂不纳入 MVP 的能力

- 完整 PaperQA2 级 PDF RAG。
- 大规模向量库和 page-level citation。
- AI-Scientist-v2 式 tree search。
- 自动代码生成和大规模沙盒实验。
- 直接 fork 外部项目作为主系统。
- 自动生成完整论文投稿稿。

## 8. 下一阶段路线

### v2.1 PDF Evidence

- 已落地 v1：PDF chunk parser、run 级 PDF evidence ingest、Evidence Ledger page 字段。
- 后续增强：自动下载/上传 PDF、自动匹配论文、claim -> page evidence、page-level citation。

### v2.2 Claim Verifier

- 已落地 v1：从报告中抽取关键 claim，逐条匹配 eligible evidence ledger，并输出 claim audit report。
- 后续增强：Qwen/embedding 语义核验、unsupported claim 自动降级或移入风险说明。

### v2.3 Research Workspace

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

- 已落地 v1：`data/workspace/{run_id}` 文件工作区。
- 已落地 v1：`research-state.json`、`research-log.md`、`run.json`、papers/evidence/hypotheses/experiments/reports/to_human artifacts。
- 后续增强：服务重启后从 workspace 恢复 run store、workspace bundle 导出、human gate 状态持久化。

### v2.4 Skill Registry

- literature-search skill
- citation-verify skill
- pdf-rag skill
- hypothesis-debate skill
- materials-pymatgen skill

### v2.5 Human Gate

- 用户选择候选假设。
- 用户接受/拒绝引用。
- 用户要求补搜特定方向。
- 用户冻结 evidence set 后再生成报告。

## 9. 参考项目取舍

| 项目 | 采用方式 |
| --- | --- |
| AutoResearchClaw | 重写并吸收多源检索、citation verification、audit log 思想 |
| PaperQA2 | 暂不直接接入，后续吸收 PDF ingest、chunk、page citation 模型 |
| GPT Researcher | 借鉴 Planner / Executor / Publisher 产品结构 |
| STORM | 借鉴多视角问题生成和 outline-before-writing |
| AI-Scientist-v2 / AIDE | 后续用于实验分支搜索，不进入当前 MVP |

## 10. 当前版本结论

PRD v2 的重点是把 TrustSci-Agent 做成“可信科研报告生成系统”。相比 PRD v1，本版本将 citation verification 和 evidence eligibility 提升为核心验收标准。只要系统能稳定证明“引用是真的、证据可追溯、报告不编文献”，就已经和普通 Deep Research 或普通 RAG 拉开差距。
