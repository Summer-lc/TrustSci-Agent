# 代码文件地图

## 1. 根目录

| 路径 | 职责 |
|---|---|
| `README.md` | 项目入口、启动方式和交接导航 |
| `PRD_v1.md` / `PRD_v2.md` / `PRD_v3.md` | 历史产品需求与领域演进 |
| `prd_v3_s*.md` | S1–S5 详细实施计划，适合理解设计来源 |
| `SESSION_HANDOFF.md` | 截至 S6 的历史交接记录，已不是完整当前状态 |
| `docker-compose.yml` | 三服务生产式本地栈 |
| `docker-compose.dev.yml` | 热重载、共享代码卷和前端开发卷 |
| `.env.example` | 安全环境变量模板 |
| `Makefile` | 常用启动、日志、冻结演示命令 |
| `scripts/check_dev_env.py` | 不打印密钥的环境自检 |
| `scripts/freeze_demo_case.py` | 冻结演示运行和生成 manifest |

## 2. 后端入口与 API

| 路径 | 职责 |
|---|---|
| `backend/app/main.py` | 创建 FastAPI、CORS、挂载路由和根健康检查 |
| `backend/app/config.py` | 从 `.env` 读取 Qwen、文献、数据、browser-worker 和引擎配置 |
| `backend/app/api/routes_runs.py` | 运行创建/启动/控制、论文/证据、baseline、报告和工作区接口 |
| `backend/app/api/routes_data.py` | 数据 profile 与材料 baseline 接口 |
| `backend/app/api/routes_browser.py` | 网页抓取、论文预览和缓存截图服务 |
| `backend/app/api/routes_system.py` | 系统配置、健康状态和 Qwen ping |

## 3. 工作流

| 路径 | 职责 |
|---|---|
| `backend/app/workflows/scientist_workflow.py` | 所有科研原子步骤、classic 路径、恢复、工作区写入 |
| `backend/app/workflows/langgraph_workflow.py` | LangGraph 节点、条件边、循环、检查点和最终化 |
| `backend/app/workflows/run_control.py` | 错误分类、可跳过步骤和运行控制信号 |

`scientist_workflow.py` 体积较大。阅读时先从 `__init__` 看依赖，再按 `run/_resume_incomplete_pipeline` 看顺序，最后只跳到感兴趣的 `_run_*` 或 `_evaluate_*` 方法。

## 4. 智能体

`backend/app/agents/` 当前约 25 个 Python 文件，按职责阅读：

- 入口：`intent_router_agent.py`、`idea_intake_agent.py`、`planner_agent.py`
- 文献：`literature_miner_agent.py`、`paper_type_classifier_agent.py`、`gap_finder_agent.py`
- 假设：`hypothesis_agent.py`、`critic_agent.py`、`critic_arena_agent.py`、`challenger_agent.py`、`hypothesis_arena_agent.py`、`novelty_checker_agent.py`、`revision_agent.py`
- baseline：`baseline_intake_agent.py`、`baseline_discovery_agent.py`、`repository_verifier_agent.py`
- 实验：`experiment_designer_agent.py`、`experiment_redesign_agent.py`、`fair_comparison_planner.py`、`code_writer_agent.py`
- 结果/报告：`result_analysis_agents.py`、`report_writer_agent.py`、`report_reviser_agent.py`、`report_translator_agent.py`
- 数据：`scientific_data_agent.py`

## 5. schemas

`backend/app/schemas/` 是前后端合同的事实来源：

- `run.py`：ResearchRun、constraints、运行生命周期和聚合状态。
- `mode.py`、`idea.py`：三模式与结构化想法。
- `paper.py`、`citation.py`、`evidence.py`、`claim.py`：文献、证据和审计。
- `baseline.py`、`baseline_intake.py`：候选与可信 baseline 输入。
- `arena.py`、`hypothesis.py`、`feedback_loop.py`：假设竞技和反馈状态。
- `experiment.py`、`code_experiment.py`、`experiment_assistance.py`：实验计划、代码执行和用户结果分析。
- `report.py`：中英文报告与系统 provenance。
- `run_control.py`：步骤状态、事件和操作请求。

修改 API 前先改 schema 和测试，再同步 `frontend/lib/api.ts`。

## 6. 工具与证据

- `backend/app/tools/qwen_client.py`：百炼调用、解析、重试、fallback 和审计。
- `backend/app/llm/`：统一 LLM 接口、registry 和 LCEL 适配。
- `literature_router.py` 与各文献 client：检索、合并和领域排序。
- `citation_verifier.py`、`claim_verifier.py`：引用和主张核验。
- `pdf_parser.py`、`browser_client.py`：论文文本与网页快照。
- `baseline_sources.py`、`code_url_extractor.py`：候选代码与仓库来源。
- `code_safety.py`、`sandbox_executor.py`：生成代码静态检查和受控运行。
- `report_pdf_exporter.py`：PDF 导出。
- `backend/app/evidence/`：账本、选择与审计。
- `backend/app/storage/`：内存索引和持久化工作区。

## 7. 前端

| 路径 | 职责 |
|---|---|
| `frontend/app/page.tsx` | 页面入口 |
| `frontend/components/workbench/Workbench.tsx` | 主要状态、请求、轮询、版本切换和三栏组合 |
| `frontend/lib/api.ts` | 后端类型和 API 客户端 |
| `frontend/lib/workbench.ts` | 原子步骤到阶段/对话的映射 |
| `ResearchConsole.tsx` | 任务和模式输入 |
| `ResearchStageNavigator.tsx` / `ResearchStageContent.tsx` | 中栏阶段导航与内容 |
| `ContextInspector.tsx` / `PaperReaderPanel.tsx` | 右栏论文阅读 |
| `RunHistory.tsx` / `ResearchConversation.tsx` | 左栏历史、对话和恢复入口 |
| 各 `*Panel.tsx` | 文献、证据、假设、baseline、实验、结果和报告面板 |

前端测试位于 `WorkbenchLayout.test.tsx` 和 `frontend/lib/workbench.test.ts`。

## 8. browser-worker 与实验

- `browser-worker/worker.py`：独立 FastAPI 抓取服务。
- `experiments/seismic_event_classification/data.py`：确定性合成波形。
- `baseline.py`：时域统计 + LogisticRegression。
- `model_template.py`：SeismicModel 接口参考。
- `tests.py`：生成模型的导入、接口和预测有效性检查。
- `train.py`：统一训练、指标与比较输出。
- `harness_manifest.json`：版本、修复轮次和验收门。

## 9. 数据与文档

- `data/seismic_demo/events.csv`：构造事件元数据。
- `data/sample_datasets/solid_electrolyte_candidates.csv`：能源材料样例。
- `data/workspace/`、`data/outputs/`：本地运行产物，默认忽略。
- `docs/`：API、架构、Qwen、前端、演示、开发流程、设计与计划。
- `项目展示/`：正式 16 页 PPT 和最终预览；构建中间物被忽略。

## 10. 推荐阅读路径

1. `backend/app/schemas/run.py`：先认识一个 run 包含什么。
2. `routes_runs.py`：了解外部怎样操作 run。
3. `langgraph_workflow.py`：看主图和条件边。
4. `scientist_workflow.py`：选择 2–3 个节点追到 agent/tool。
5. `qwen_client.py` 与 `langchain_adapter.py`：理解真实调用和 fallback。
6. `code_safety.py`、`sandbox_executor.py`、实验 harness：理解可执行实验。
7. `Workbench.tsx`、`api.ts`、`workbench.ts`：理解界面如何消费状态。
8. 选择一个后端测试和一个前端测试，沿断言反向阅读实现。

