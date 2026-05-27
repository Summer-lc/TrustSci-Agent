# Multi-Agent AI Scientist 系统 PRD v1

## 1. 项目名称

暂定：

**TrustSci-Agent：面向高价值科研问题的可信多智能体 AI Scientist 系统**

也可以叫：

**EvidenceMind Scientist：基于证据链与多智能体辩论的可验证科研假设生成平台**

最终参赛名称建议偏正式：

> **基于 Qwen 的可信多智能体 AI Scientist：从文献证据链到可验证科学假设生成**

---

## 2. 项目目标

开发一个独立的 Multi-Agent AI Scientist 系统，围绕特定科学领域，自动完成：

**科研问题理解 → 文献/数据检索 → 事实抽取 → 引用核验 → 知识缺口识别 → 假设生成 → 多智能体辩论 → 实验设计 → 标准化研究计划输出。**

核心不是“自动写论文”，而是：

> **生成带真实文献依据、可追溯证据链、可执行验证路径的《科学假设与研究计划》。**

---

## 3. 参赛定位

比赛关注三类评分：

| 评分项  | 分值 | 我们的对应设计                               |
| ---- | -: | ------------------------------------- |
| 科学价值 | 40 | 选择高价值科学问题，生成创新、自洽、可验证假设               |
| 技术深度 | 30 | 自研多智能体架构 + Qwen + 文献/数据多工具处理 + 浏览器自动化 |
| 应用潜力 | 30 | 前端可交互、代码可复现、真实案例、可导出报告                |

系统必须体现：

1. **基于 Qwen / 百炼 API。**
2. **有多智能体协作，而不是单轮聊天。**
3. **有文献和数据输入。**
4. **有证据链和引用核验。**
5. **有人在回路和多轮迭代。**
6. **最终输出符合比赛字段规范。**

---

## 4. 不做什么

第一版不要做这些：

1. 不做通用论文自动生成器。
2. 不做完全自主的“端到端科研闭环”大而全系统。
3. 不做复杂模型微调。
4. 不强绑定 SeisLLM / EHS / 地震方向。
5. 不直接 fork Hermes / OpenClaw 改成参赛系统。
6. 不依赖单一大模型自由生成 References。
7. 不做无法验证的“重大发现”式夸张叙事。

---

## 5. 推荐示范领域

系统设计成**领域可插拔**，但第一版必须有一个高质量 demo case。

推荐主 demo：

### 方向 A：能源材料 / 固态电池 / 催化剂发现

优势：

* AI for Science 属性强；
* 公共数据库多；
* 顶刊顶会认可度高；
* 容易做“结构—性能—实验验证”闭环；
* 避免地震方向刻板印象。

示范问题可以是：

> 基于近年文献和开放材料数据库，自动生成提升固态电解质离子电导率与稳定性的可验证科学假设。

备选 demo：

### 方向 B：药物靶点发现 / 生物医学假设生成

优势是科学价值高，劣势是验证难度和合规复杂度更高。

### 方向 C：气候极端事件 / 遥感多模态分析

优势是自然科学价值高，劣势是数据处理链路更重。

**第一版建议选能源材料。**

---

# 6. 用户故事

## 用户故事 1：科研问题输入

作为参赛评委或科研用户，我输入：

> 我想研究固态电解质材料中离子电导率提升的潜在机制，请基于真实文献和开放数据库生成可验证研究假设。

系统应该返回：

* 拆解后的研究子问题；
* 需要检索的关键词；
* 计划查询的文献库和数据库；
* 后续 Agent 工作流。

---

## 用户故事 2：文献证据收集

系统应该自动完成：

* 搜索论文；
* 获取标题、作者、年份、DOI、摘要；
* 下载或解析 PDF；
* 抽取关键事实；
* 校验引用真实性；
* 建立 Evidence Ledger。

---

## 用户故事 3：假设生成与辩论

系统应该生成 3–5 个候选假设，并由 Critic Agent 评价：

* 新颖性；
* 自洽性；
* 与已有工作的区别；
* 可验证性；
* 数据可获得性；
* 潜在风险。

---

## 用户故事 4：实验计划生成

系统应该为选定假设生成：

* 数据集；
* Source / Target；
* baseline；
* metrics；
* 实验流程；
* 预期结果；
* 失败风险；
* 后续验证路径。

---

## 用户故事 5：报告导出

系统最终导出一份结构化报告：

```text
Problem Statement
Rationale
Technical Details
Datasets
Source
Target
Paper Title
Paper Abstract
Methods
Experiments
Results
References
Citation Audit Log
```

---

# 7. 系统核心功能模块

## 7.1 Research Planner Agent

作用：把用户输入的模糊科研方向转成可执行任务。

输入：

```json
{
  "domain": "energy materials",
  "question": "提升固态电解质离子电导率的机制假设",
  "constraints": ["must use real papers", "must design verifiable experiment"]
}
```

输出：

```json
{
  "sub_questions": [
    "现有固态电解质离子电导率提升的主要机制有哪些？",
    "哪些结构特征与高离子电导率相关？",
    "哪些公开数据集可以支持验证？"
  ],
  "search_queries": [
    "solid-state electrolyte ionic conductivity mechanism",
    "structure property relationship solid electrolyte",
    "machine learning solid electrolyte materials"
  ],
  "tools_to_call": [
    "openalex_search",
    "crossref_verify",
    "pdf_parser",
    "materials_database_query"
  ]
}
```

---

## 7.2 Browser Research Agent

作用：参考 Hermes 的浏览器自动化能力，完成网页级资料采集。

第一版不一定要让它完全自主点击网页，可以先做半自动：

* 打开搜索结果；
* 访问论文主页；
* 保存网页快照；
* 提取标题、摘要、DOI；
* 下载 PDF；
* 保存访问日志。

技术建议：

* Playwright；
* browser-worker 独立 Docker 容器；
* 后端通过 API 调用 browser-worker；
* 每次浏览器动作保存 screenshot / html / metadata。

---

## 7.3 Literature Miner Agent

作用：从论文中抽取结构化事实。

抽取字段：

```json
{
  "paper_id": "paper_001",
  "research_problem": "...",
  "method": "...",
  "dataset": "...",
  "key_findings": ["...", "..."],
  "limitations": ["...", "..."],
  "possible_transfer": ["...", "..."]
}
```

要求：

* 每个事实必须绑定论文来源；
* 关键事实尽量绑定 PDF 页码或段落；
* 对不确定内容标记 uncertain。

---

## 7.4 Citation Verifier Agent

这是系统的核心护城河。

功能：

1. 校验 DOI 是否存在。
2. 校验标题、作者、年份是否匹配。
3. 校验模型生成的引用是否来自已检索文献。
4. 禁止 Report Writer 新增未验证引用。
5. 输出 citation audit log。

引用状态设计：

```json
{
  "paper_id": "paper_001",
  "title": "...",
  "doi": "...",
  "verified_by": ["crossref", "openalex", "pdf"],
  "title_match_score": 0.96,
  "year_match": true,
  "status": "verified"
}
```

---

## 7.5 Scientific Data Agent

作用：查询开放科学数据库，支撑“可验证”。

材料方向可以先抽象成：

```text
data_sources/
  materials_project_adapter.py
  matbench_adapter.py
  open_catalyst_adapter.py
  local_csv_adapter.py
```

第一版不需要打通所有数据库，可以先支持：

* 用户上传 CSV；
* 系统读取 sample dataset；
* 生成数据 profile；
* 输出字段、样本量、缺失值、可用任务类型。

---

## 7.6 Gap Finder Agent

作用：根据文献事实和数据 profile 找知识缺口。

输出示例：

```json
{
  "gap": "现有研究较多关注组成特征，但较少系统融合文献机制描述与局部结构环境特征。",
  "evidence": ["evidence_001", "evidence_007"],
  "potential_value": "可能提升材料性质预测的可解释性和泛化能力"
}
```

---

## 7.7 Hypothesis Generator Agent

作用：生成多个候选科研假设。

假设结构：

```json
{
  "hypothesis_id": "H1",
  "statement": "...",
  "rationale": "...",
  "supporting_evidence": ["evidence_001", "evidence_002"],
  "novelty_claim": "...",
  "verification_path": "..."
}
```

---

## 7.8 Critic / Debate Agent

作用：像评审专家一样反驳假设。

评价维度：

```json
{
  "novelty": 8,
  "self_consistency": 7,
  "verifiability": 9,
  "data_availability": 8,
  "risk": "可能与已有 structure-aware GNN 工作重合，需要进一步 novelty check"
}
```

辩论流程：

```text
Generator 提出 H1
→ Critic 指出问题
→ Generator 修改 H1
→ Verifier 检查证据
→ Human 选择是否接受
```

---

## 7.9 Experiment Designer Agent

作用：把假设转成可执行验证计划。

输出：

```json
{
  "datasets": ["Matbench-like dataset", "user uploaded dataset"],
  "baselines": ["composition-only model", "structure-only model"],
  "metrics": ["MAE", "R2", "top-k hit rate"],
  "experiment_steps": [
    "构建 composition-only baseline",
    "构建 structure-aware baseline",
    "加入 literature-derived mechanism features",
    "比较性能和消融结果"
  ],
  "expected_results": "...",
  "failure_modes": ["数据量不足", "特征泄漏", "文献特征难以结构化"]
}
```

---

## 7.10 Report Writer Agent

作用：最终报告生成。

严格限制：

* 只能使用 verified evidence；
* 只能使用 verified references；
* 必须输出比赛规定字段；
* 必须附 Citation Audit Log；
* 不确定内容必须标记为“待验证”。

---

# 8. 技术架构

## 8.1 总体架构

```text
Frontend 科研工作台
        |
        v
FastAPI Backend
        |
        |-- Agent Orchestrator
        |-- Qwen Client / Bailian API
        |-- Tool Registry
        |-- Evidence Ledger
        |-- Citation Verifier
        |-- Report Generator
        |
        |-- Browser Worker / Playwright
        |-- PDF Parser
        |-- Literature APIs
        |-- Scientific Data Adapters
        |
        v
PostgreSQL + Vector DB + File Storage
```

---

## 8.2 推荐技术栈

| 层级       | 技术                                     |
| -------- | -------------------------------------- |
| 前端       | Next.js + React + Tailwind + shadcn/ui |
| 后端       | FastAPI + Python 3.11                  |
| Agent 编排 | 自研轻量状态机，后续可接 LangGraph                 |
| LLM      | 百炼 Qwen API                            |
| 浏览器自动化   | Playwright                             |
| PDF 解析   | PyMuPDF / pdfplumber / marker 可选       |
| 向量库      | Chroma 或 Qdrant                        |
| 数据库      | PostgreSQL                             |
| 队列       | Redis + RQ / Celery，MVP 可先不用           |
| 部署       | Docker Compose                         |
| 开发       | VSCode Remote SSH + Codex 插件           |
| 辅助       | Hermes / OpenClaw 用于网页任务、调研、批量操作辅助     |

---

# 9. 仓库结构

```text
trustsci-agent/
  README.md
  docker-compose.yml
  .env.example
  docs/
    PRD.md
    ARCHITECTURE.md
    ROADMAP.md
    DEMO_SCRIPT.md
    SUBMISSION_CHECKLIST.md

  backend/
    Dockerfile
    requirements.txt
    app/
      main.py
      config.py

      api/
        routes_runs.py
        routes_papers.py
        routes_evidence.py
        routes_hypotheses.py
        routes_reports.py

      schemas/
        run.py
        paper.py
        evidence.py
        hypothesis.py
        experiment.py
        report.py

      agents/
        planner_agent.py
        literature_miner_agent.py
        citation_verifier_agent.py
        data_agent.py
        gap_finder_agent.py
        hypothesis_agent.py
        critic_agent.py
        experiment_designer_agent.py
        report_writer_agent.py

      workflows/
        scientist_workflow.py
        states.py

      tools/
        qwen_client.py
        openalex_client.py
        crossref_client.py
        semantic_scholar_client.py
        arxiv_client.py
        pdf_parser.py
        browser_client.py
        citation_utils.py
        dataset_profiler.py

      evidence/
        ledger.py
        verifier.py
        audit.py

      storage/
        db.py
        models.py
        vector_store.py
        file_store.py

      prompts/
        planner.md
        literature_miner.md
        hypothesis_generator.md
        critic.md
        experiment_designer.md
        report_writer.md

      tests/
        test_citation_verifier.py
        test_workflow_mock.py

  browser-worker/
    Dockerfile
    worker.py
    playwright_tools.py

  frontend/
    Dockerfile
    package.json
    app/
      page.tsx
      runs/
      evidence/
      hypotheses/
      reports/
    components/
      ResearchInput.tsx
      EvidenceBoard.tsx
      HypothesisArena.tsx
      DebatePanel.tsx
      ReportViewer.tsx
      RunTimeline.tsx

  data/
    sample_papers/
    sample_datasets/
    outputs/
```

---

# 10. API 设计

## 10.1 创建科研任务

```http
POST /api/runs
```

请求：

```json
{
  "domain": "energy_materials",
  "question": "如何提升固态电解质材料的离子电导率和稳定性？",
  "constraints": {
    "must_verify_citations": true,
    "max_papers": 10,
    "require_experiment_plan": true
  }
}
```

返回：

```json
{
  "run_id": "run_001",
  "status": "created"
}
```

---

## 10.2 启动工作流

```http
POST /api/runs/{run_id}/start
```

---

## 10.3 查看任务状态

```http
GET /api/runs/{run_id}
```

返回：

```json
{
  "run_id": "run_001",
  "status": "running",
  "current_stage": "citation_verification",
  "progress": 0.45
}
```

---

## 10.4 查看证据

```http
GET /api/runs/{run_id}/evidence
```

---

## 10.5 查看候选假设

```http
GET /api/runs/{run_id}/hypotheses
```

---

## 10.6 人在回路选择假设

```http
POST /api/runs/{run_id}/hypotheses/{hypothesis_id}/select
```

---

## 10.7 生成最终报告

```http
POST /api/runs/{run_id}/report
```

---

## 10.8 导出报告

```http
GET /api/runs/{run_id}/report/export?format=pdf
```

---

# 11. 前端页面设计

## 页面 1：Research Console

功能：

* 输入科研问题；
* 选择领域；
* 选择文献数量；
* 选择是否启用浏览器自动化；
* 启动任务。

---

## 页面 2：Run Timeline

展示多智能体执行过程：

```text
Planner Agent completed
Literature Search running
Citation Verification pending
Hypothesis Generation pending
Critic Review pending
Report Writing pending
```

这个页面很适合录演示视频。

---

## 页面 3：Evidence Board

展示：

* 论文标题；
* DOI；
* 作者年份；
* 验证状态；
* 抽取事实；
* 对应 claim；
* PDF 页码或证据片段。

---

## 页面 4：Hypothesis Arena

展示：

* H1 / H2 / H3；
* 支撑证据；
* novelty 分数；
* verifiability 分数；
* critic 反驳；
* revised hypothesis。

---

## 页面 5：Experiment Plan

展示：

* dataset；
* baseline；
* metrics；
* experiment steps；
* expected results；
* risk control。

---

## 页面 6：Final Report

展示比赛规范字段，并支持导出：

* Markdown；
* PDF；
* JSON。

---

# 12. 开发工具策略

## 12.1 VSCode + Codex：主开发工具

用于：

* 写代码；
* 改 bug；
* 运行测试；
* 前后端联调；
* Docker 配置；
* 重构；
* 写 README；
* 生成接口文档；
* 控制 Git diff。

优势：

* 文件结构清楚；
* 可控性高；
* 适合远程 Docker；
* 适合长期工程；
* 每次改动可 review；
* 不容易让智能体乱改全项目。

---

## 12.2 Hermes / OpenClaw：辅助开发工具

用于：

* 自动浏览网页；
* 搜索参考项目；
* 收集 API 文档；
* 批量打开论文页面；
* 下载资料；
* 总结网页；
* 设计可复用技能；
* 辅助做 demo 资料采集。

不建议让 Hermes 直接长期修改主仓库，除非你能很好地控制它的修改范围。

最合理的用法：

```text
VSCode + Codex：写主代码
Hermes：跑网页/资料/浏览器任务
OpenClaw：参考设备控制和自动化操作
Qwen/Bailian：参赛系统核心模型调用
```

---

# 13. 开发阶段路线图

## Phase 0：项目初始化，1–2 天

目标：搭好工程骨架。

任务：

1. 建 Git 仓库。
2. 建 Docker Compose。
3. 搭 FastAPI。
4. 搭 Next.js。
5. 搭 PostgreSQL。
6. 写 README。
7. 写 .env.example。
8. 后端返回 mock run。
9. 前端能创建 mock task。

验收标准：

```text
docker compose up 后，前端和后端都能访问。
前端输入一个 research question，后端返回 run_id。
```

---

## Phase 1：Qwen Client 与基础 Agent，2–3 天

目标：打通百炼 Qwen API。

任务：

1. 实现 qwen_client.py。
2. 实现统一 LLM 调用接口。
3. 写 Planner Agent。
4. 写 Report Writer mock。
5. 每次调用记录 prompt、response、model、token、时间。

验收标准：

```text
输入科研问题后，Planner Agent 能生成 search_queries、sub_questions、workflow_plan。
```

注意：比赛要求通过百炼调用模型 API 并提供凭证/截图，所以从第一天就要保存调用日志和截图素材。

---

## Phase 2：文献检索与 Citation Verifier，5–7 天

目标：系统能拿到真实论文，而不是模型编论文。

任务：

1. 接 OpenAlex。
2. 接 Crossref。
3. 接 Semantic Scholar，可选。
4. 接 arXiv，可选。
5. 标准化 PaperSchema。
6. 实现 DOI 校验。
7. 实现 title fuzzy match。
8. 实现 author/year match。
9. 实现 verified / suspicious / rejected 状态。

验收标准：

```text
输入关键词后，系统返回 5–10 篇真实论文。
每篇论文有 title、authors、year、doi/source_url、verified 状态。
最终报告不能引用 rejected paper。
```

这是第一优先级模块。

---

## Phase 3：PDF 解析与事实抽取，5–7 天

目标：系统能从论文内容里抽取事实。

任务：

1. 支持用户上传 PDF。
2. 支持解析 PDF 文本。
3. 支持按 section 分块。
4. Literature Miner 抽取事实。
5. 每个事实绑定 paper_id。
6. 建 Evidence Ledger。

验收标准：

```text
上传 3 篇 PDF 后，系统能抽取研究问题、方法、数据集、结论、局限性。
每条 evidence 都能追溯到 paper_id。
```

---

## Phase 4：Browser Worker，4–6 天

目标：实现 Hermes 风格的网页采集能力。

任务：

1. 建 browser-worker 容器。
2. Playwright 打开网页。
3. 截图保存。
4. HTML 保存。
5. 提取 title、meta、links。
6. 下载 PDF 链接。
7. 每个浏览动作写入 browser_trace。

验收标准：

```text
给定论文页面 URL，browser-worker 能保存页面截图、HTML、PDF 链接和元信息。
```

第一版不追求完全自主网页 Agent，先把工具能力做出来。

---

## Phase 5：Hypothesis Generator + Critic，5–7 天

目标：多智能体假设生成和辩论跑通。

任务：

1. Gap Finder 总结知识缺口。
2. Hypothesis Agent 生成 3 个候选假设。
3. Critic Agent 逐条反驳。
4. Hypothesis Agent 修改假设。
5. 人在回路选择最终假设。
6. 每个假设绑定 evidence_id。

验收标准：

```text
系统能生成 H1/H2/H3，每个假设都有支撑证据、critic 评价和 revised version。
```

---

## Phase 6：Experiment Designer，4–6 天

目标：把假设变成可验证计划。

任务：

1. 设计数据集字段。
2. 设计 baseline。
3. 设计 metrics。
4. 设计实验流程。
5. 生成 failure mode。
6. 支持小型 sample dataset profile。

验收标准：

```text
选定 H1 后，系统能输出 Datasets、Source、Target、Methods、Experiments、Metrics、Expected Results。
```

比赛要求 Results 可以通过公式推导或实际执行在一定范围内验证可行性，所以第一版至少要有“toy experiment / sample result card”。

---

## Phase 7：前端工作台，7–10 天

目标：做一个适合演示的视频级前端。

页面优先级：

1. Research Console。
2. Run Timeline。
3. Evidence Board。
4. Hypothesis Arena。
5. Final Report。

验收标准：

```text
能完整演示一次从输入问题到报告导出的流程。
```

---

## Phase 8：报告导出与材料整理，5–7 天

目标：参赛材料成型。

任务：

1. 导出 Markdown。
2. 导出 PDF。
3. 生成 Citation Audit Log。
4. 生成 README。
5. 写技术方案 PDF 初稿。
6. 准备 10 分钟演示视频脚本。
7. 截图百炼调用凭证。
8. 打包代码和 demo outputs。

验收标准：

```text
一个外部人按照 README 能用 sample data 跑通 demo。
```

---

# 14. MVP 版本定义

## MVP 必须完成

```text
1. 输入科研问题
2. Qwen Planner 拆解任务
3. 检索真实论文
4. 校验引用
5. 抽取文献事实
6. 生成 evidence board
7. 生成 3 个候选假设
8. Critic 反驳和迭代
9. 生成实验计划
10. 导出标准报告
```

## MVP 可以不做

```text
1. 大规模自动实验
2. 模型微调
3. 完整自主浏览器智能体
4. 多用户权限系统
5. 复杂知识图谱
6. 分布式任务调度
```

---

# 15. 版本规划

## v0.1：工程骨架

* FastAPI + Next.js + Docker；
* mock workflow；
* mock report。

## v0.2：Qwen Agent Workflow

* Planner；
* Hypothesis；
* Report Writer；
* prompt logging。

## v0.3：真实文献检索

* OpenAlex / Crossref；
* PaperSchema；
* Citation Verifier。

## v0.4：PDF + Evidence

* PDF parser；
* Literature Miner；
* Evidence Ledger。

## v0.5：假设辩论

* Gap Finder；
* Hypothesis Generator；
* Critic Agent；
* Human selection。

## v0.6：实验计划

* Experiment Designer；
* dataset profiler；
* toy result card。

## v0.7：前端演示版

* Research Console；
* Timeline；
* Evidence Board；
* Hypothesis Arena；
* Report Viewer。

## v1.0：参赛提交版

* 技术方案 PDF；
* 10 分钟视频；
* README；
* demo 数据；
* 代码可复现；
* 百炼截图；
* citation audit log。

---

# 16. 核心数据模型

## Paper

```python
class Paper(BaseModel):
    id: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    venue: str | None
    abstract: str | None
    source_url: str | None
    pdf_url: str | None
    verified_status: Literal["verified", "suspicious", "rejected"]
```

## Evidence

```python
class Evidence(BaseModel):
    id: str
    paper_id: str
    claim: str
    evidence_text: str
    section: str | None
    page: int | None
    confidence: float
    verified: bool
```

## Hypothesis

```python
class Hypothesis(BaseModel):
    id: str
    statement: str
    rationale: str
    supporting_evidence_ids: list[str]
    novelty_score: float
    verifiability_score: float
    risk: str
    critic_comments: list[str]
    revised_statement: str | None
```

## ExperimentPlan

```python
class ExperimentPlan(BaseModel):
    hypothesis_id: str
    datasets: list[str]
    source_data: str
    target_data: str
    baselines: list[str]
    metrics: list[str]
    methods: list[str]
    expected_results: str
    failure_modes: list[str]
```

## FinalReport

```python
class FinalReport(BaseModel):
    problem_statement: str
    rationale: str
    technical_details: str
    datasets: str
    source: str
    target: str
    paper_title: str
    paper_abstract: str
    methods: str
    experiments: str
    results: str
    references: list[Paper]
    citation_audit_log: list[dict]
```

---

# 17. 每天开发工作流

建议你每天按这个节奏：

```text
1. 早上：明确今天只做一个模块
2. Codex：生成或修改代码
3. 手动 review diff
4. 运行测试
5. Docker 环境验证
6. 记录今天完成内容到 docs/DEV_LOG.md
7. 晚上：让 Hermes/OpenClaw 辅助查资料或整理参考项目
8. 把有效资料沉淀到 docs/RESEARCH_NOTES.md
```

原则：

> **Codex 改代码，Hermes 查资料，Qwen 跑系统，Git 管版本。**

---

# 18. 给 Codex 的长期总 Prompt

你可以在 Codex 插件里长期使用这个项目背景：

```text
我正在开发一个用于挑战杯“基于国产开源大模型的 AI Scientist 的研发与应用”比赛的系统，项目名 TrustSci-Agent。

系统目标：
基于阿里云百炼 Qwen API，自研一个 Multi-Agent AI Scientist 系统，实现从科研问题输入、文献检索、事实抽取、引用核验、知识缺口识别、假设生成、多智能体辩论、实验设计到最终《科学假设与研究计划》输出的闭环。

技术栈：
- Backend: FastAPI + Python 3.11
- Frontend: Next.js + React + Tailwind + shadcn/ui
- Browser Worker: Playwright
- DB: PostgreSQL
- Vector DB: Chroma 或 Qdrant
- Deployment: Docker Compose

核心约束：
1. 所有核心模型调用通过 qwen_client.py 封装，后续接入百炼 Qwen API。
2. References 不能虚构，最终报告只能引用 Citation Verifier 验证过的论文。
3. 每个关键 claim 必须绑定 Evidence。
4. Multi-Agent workflow 必须结构清晰，可调试，可复现。
5. 不要一次性生成过多复杂代码，优先保证模块边界清晰、测试可运行。
6. 新增功能时同步更新 README 或 docs。
```

---

# 19. 给 Hermes / OpenClaw 的辅助 Prompt

Hermes / OpenClaw 更适合这样用：

```text
请作为科研资料采集智能体，帮我调研“AI Scientist、AI Co-Scientist、SciAgents、自动科研假设生成、文献引用核验、evidence-grounded generation”相关开源项目和论文。

目标：
1. 找到项目名称、论文链接、GitHub 链接；
2. 总结它们的系统架构；
3. 重点关注它们如何做 literature search、hypothesis generation、critique/review、experiment planning、citation verification；
4. 不要生成虚构引用；
5. 每条结论都给出来源；
6. 输出为 Markdown 表格，方便我放入 docs/RESEARCH_NOTES.md。
```

另一个用于浏览器自动化设计的 prompt：

```text
请帮我观察并总结几个自动科研工具的浏览器/工具调用能力，重点关注：
1. 是否支持打开网页；
2. 是否支持下载 PDF；
3. 是否支持保存网页快照；
4. 是否支持技能沉淀；
5. 是否支持多工具调用；
6. 这些能力如何迁移到我自己的 FastAPI + Playwright browser-worker 设计中。
```

---

# 20. 风险清单

## 风险 1：系统看起来像普通 RAG

解决：

* 必须展示多 Agent 流程；
* 必须展示 Critic 辩论；
* 必须展示 Evidence Ledger；
* 必须展示 Citation Audit Log；
* 必须展示实验计划。

## 风险 2：引用幻觉

解决：

* Report Writer 禁止新增引用；
* References 只能来自 verified papers；
* 论文元数据必须经过 Crossref / OpenAlex 等校验；
* 报告附 audit log。

## 风险 3：demo 领域太泛

解决：

* 系统通用，demo 垂直；
* 第一版聚焦能源材料；
* 所有样例围绕一个科学问题展开。

## 风险 4：开发范围失控

解决：

* MVP 只做一个完整闭环；
* 不做微调；
* 不做复杂知识图谱；
* 不做大规模实验；
* 不做多用户系统。

## 风险 5：前端拖慢进度

解决：

* 前端只做演示级工作台；
* 数据可先用后端 mock；
* 优先 Run Timeline、Evidence Board、Report Viewer。

---

# 21. 最终提交材料规划

你最后应该提交：

```text
1. 技术方案 PDF，不超过 20 页
2. 源代码
3. README
4. Docker Compose
5. demo 数据
6. demo 输出报告
7. Citation Audit Log
8. 百炼 API 调用截图
9. 前端截图
10. 10 分钟内演示视频
```

技术方案 PDF 目录建议：

```text
1. 项目背景与问题定义
2. 研究目标与应用场景
3. 系统总体架构
4. 基于 Qwen 的多智能体协作设计
5. 文献挖掘与事实抽取
6. 引用核验与证据链机制
7. 假设生成、辩论与人在回路
8. 实验计划生成与可验证性设计
9. 前端系统与真实案例演示
10. 代码复现与部署说明
11. 创新点、局限性与后续计划
```

---

# 22. 最终开发建议

你的理解没问题：**Hermes 可以作为开发工具和自动化助手，不是系统框架。**

但主线仍然建议：

> **VSCode + Codex 做主工程开发，Hermes / OpenClaw 做资料采集和浏览器自动化辅助，最终系统独立实现。**

最适合你当前情况的路线是：

```text
主开发环境：远程 Linux 服务器 + Docker + VSCode Remote SSH
主开发助手：Codex 插件
辅助智能体：Hermes / OpenClaw
核心模型：百炼 Qwen
系统架构：自研 Multi-Agent
核心卖点：可信证据链 + 引用核验 + 多智能体辩论 + 可验证实验设计
首个 demo：能源材料 / 固态电解质方向
```

这样既能利用 GPT-5.5 / Hermes 这类强开发智能体的能力，又不会让参赛作品变成“工具套壳”。评委看到的是一个清晰、独立、可复现、符合赛题要求的 AI Scientist 系统。
