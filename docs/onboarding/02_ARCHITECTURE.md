# 整体架构

## 1. 架构目标

TrustSci-Agent 不是单一分类模型，而是围绕科研任务建立证据可追踪、结果可审计、实验可复现的多智能体工作台。系统把“语言模型推理”“确定性工具”“受控代码执行”和“人工检查”分开，避免所有能力都被模糊描述为大模型生成。

## 2. 服务架构

```text
浏览器
  │
  ▼
Next.js frontend :3000
  │ REST / polling
  ▼
FastAPI backend :8000
  ├─ 工作流：ScientistWorkflow / LangGraphWorkflow
  ├─ 智能体：规划、文献、假设、批判、实验、报告
  ├─ 工具：文献 API、引用核验、PDF、数据、代码安全
  ├─ 存储：run store + data/workspace + data/outputs
  └─ QwenClient ──► 阿里云百炼兼容接口
  │
  └──────────────► browser-worker :8010
                     └─ HTML / screenshot / PDF link / cached preview
```

| 服务 | 入口 | 职责 | 关键依赖 |
|---|---|---|---|
| frontend | `frontend/app/page.tsx`、`Workbench.tsx` | 任务配置、轮询、阶段导航、论文阅读、结果与报告展示 | React、Next.js、FastAPI |
| backend | `backend/app/main.py` | API、运行状态、科研编排、报告与工作区导出 | FastAPI、Pydantic、LangGraph、Qwen |
| browser-worker | `browser-worker/worker.py` | 网页抓取、截图、PDF 链接和缓存 | Playwright、共享数据目录 |

## 3. 后端六层

### 3.1 API 层

`backend/app/api/` 把系统能力分成 runs、data、browser、system 四组。API 只负责校验、状态冲突和调用工作流/工具；复杂科研逻辑不应继续堆入路由。

### 3.2 编排层

- `ScientistWorkflow`：共享每个原子科研步骤，也提供 classic 线性执行和恢复逻辑。
- `LangGraphWorkflow`：继承共享步骤，用 `StateGraph` 定义三模式分支、人工检查点、重搜、实验重设计和结束条件。
- `run_control.py`：定义可跳过步骤、错误分类与运行控制信号。

前端推荐 V3 使用 `WORKFLOW_ENGINE=langgraph`。代码仍保留 classic，用于兼容和较简单的线性路径。

### 3.3 智能体层

智能体位于 `backend/app/agents/`，每个角色处理一个明确问题：

- 入口与计划：IntentRouter、IdeaIntake、Planner。
- 文献与证据：LiteratureMiner、PaperTypeClassifier、GapFinder。
- 假设：Hypothesis、Critic、CriticArena、Challenger、HypothesisArena、NoveltyChecker、Revision。
- baseline 与实验：BaselineIntake、BaselineDiscovery、RepositoryVerifier、ExperimentDesigner、ExperimentRedesign、FairComparisonPlanner、CodeWriter。
- 结果与报告：ResultEvaluator、Ablation、ResultInterpreter、ReportWriter、ReportReviser、ReportTranslator。

部分 agent 使用 LCEL 适配 Qwen，所有 agent 必须提供无 Key fallback。

### 3.4 工具层

确定性工具负责可核验工作：OpenAlex/Crossref/Semantic Scholar/arXiv、文献路由、引用和主张核验、PDF 解析、材料/地震数据、browser client、baseline 来源、代码 URL 提取、报告 PDF 导出和 Qwen 调用日志。

### 3.5 数据与存储层

- `run_store`：当前进程中的运行索引。
- `data/workspace/run_*`：每个任务的状态、研究日志、论文、证据、假设、实验和报告快照。
- `data/outputs/`：报告、LLM 审计、结果卡和导出包。
- `RunWorkspace`：写入、读取、导出和恢复运行工作区。

GitHub 不上传原始本地工作区和完整 LLM 日志，原因见 [GitHub 内容边界](11_GITHUB_CONTENTS.md)。

### 3.6 受控实验层

`experiments/seismic_event_classification/` 提供不可由 LLM 修改的固定协议：数据生成、baseline、测试、训练、指标和 manifest。LLM 只生成符合 `fit/predict` 接口的 `model.py`。`SandboxExecutor` 把固定文件与模型源码复制到单次运行目录，仅允许执行 `tests.py` 和 `train.py`。

## 4. 前端信息架构

当前工作台为三栏：

```text
左：研究对话、任务控制、显式选择历史运行
中：计划 → 证据 → 假设 → baseline → 实验 → 报告
右：当前论文/PDF/网页快照与上下文检查
```

核心状态由 `Workbench.tsx` 管理，`frontend/lib/api.ts` 定义后端类型与请求，`frontend/lib/workbench.ts` 将原子步骤归并为用户能理解的阶段。

## 5. 信任边界

- 引用元数据核验不等于论文结论正确。
- 网页快照只帮助阅读，不改变引用验证结果。
- Qwen fallback 能验证流程，不代表真实模型能力。
- 用户提交的实验代码在 experiment_assistance 模式下只作为分析输入，不会直接执行。
- 自动代码实验只执行系统生成且通过静态规则的 `model.py`，但当前隔离仍不是生产级安全边界。
- 合成数据结果只能验证软件闭环。

## 6. 建议先看的源码

1. `backend/app/main.py`
2. `backend/app/api/routes_runs.py`
3. `backend/app/workflows/langgraph_workflow.py`
4. `backend/app/workflows/scientist_workflow.py`
5. `backend/app/schemas/run.py`
6. `frontend/components/workbench/Workbench.tsx`
7. `frontend/lib/api.ts`
8. `experiments/seismic_event_classification/`

更细的文件职责见 [代码文件地图](08_CODEBASE_MAP.md)。
