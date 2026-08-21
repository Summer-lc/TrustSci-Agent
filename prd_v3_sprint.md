# v3 Sprint 重排设计

更新时间：2026-06-29
状态：设计稿（待用户评审 → 转 writing-plans）

## 0. 背景与重排动机

PRD_v3.md §14.2 原有的 Sprint 规划（V3-1 ~ V3-6）是在以下基础设施**尚未存在**时写的：
LangGraph 骨架、LangChain 适配器、前端版本切换器壳、Mode Selector UI。
现在这些都已落地（见下「现状基线」），原 Sprint 规划需要重排以：
1. 不重复已做的工作；
2. 让 LangGraph 图从「线性 → 分支 → 循环 → 回退」渐进生长；
3. 在 1–2 个月内交付**完整 v3**（三种模式 + 竞技 + 双层 ReAct + Switchback + Baseline Discovery）。

## 1. 关键决策（已与用户确认）

| 决策点 | 选择 | 备注 |
|---|---|---|
| 交付目标 | 完整 v3 | 三种入口模式 + 排名/消融竞技 + 双层 ReAct + 假设回退 + Baseline Discovery 全做 |
| 时间窗 | 1–2 个月 | 约 7 个 1 周 Sprint |
| 编排基座 | 基于 LangChain 生态 | agent 走 LCEL 链（复用 `LLMClientRunnable`）、工具走 LangChain `@tool`、分支/循环/回退走 LangGraph `StateGraph`；不退回手写状态机 |
| S6 API | 先做 demo 子集 | 扩展 `GET /api/runs/{id}` 返回 v3 字段 + 仅 2–3 个演示端点；看进度再决定是否补全 20+ 端点 |
| S7 数据集 | 开发期用构造 subset，S7 接真实公开小数据集 | 真实公开小集由 Claude 帮选 + 写 `SeismicDataAdapter`；开发期（S1–S6）用构造 subset 不被外部下载卡住；接真实集看开发进度 |

## 2. 现状基线（已落地，不重做）

- **v1/v2 线性闭环完整**：`ScientistWorkflow` 跑通 planner → literature_search → citation_verification → evidence_ledger → literature_mining → scientific_data_profile → hypothesis_debate → experiment_design → report_writer → claim_verification → report_revision → claim_reverification → report_translation。
- **LangGraph 线性骨架**：`langgraph_workflow.py` 的 `LangGraphWorkflow` 继承 `ScientistWorkflow`，用 `StateGraph(WorkflowState)` 镜像线性链，`ResearchRun` 整体作为单一 channel（`Annotated[ResearchRun, _replace]`），guided 暂停用 `interrupt()` + `Command(resume=...)`。`WORKFLOW_ENGINE=langgraph|classic` 可切换，默认 classic。
- **LangChain 适配器**：`llm/langchain_adapter.py`（`LLMClientRunnable` + `FallbackParser` + `build_agent_prompt`）把 `LLMClient` 包成 LangChain Runnable，仍走 `QwenClient.complete()`，审计日志不变。
- **LangChain 工具**：`tools/langchain_literature_tools.py`（OpenAlex/arXiv 检索 + Crossref 核验封装为 Tool）。
- **前端壳**：`Workbench.tsx` 有 Classic / Seismic Expert 双入口卡 + 顶栏切换；`ResearchConsole.tsx` 有 `WorkbenchVersion` + `ResearchMode` 类型与选择器；Seismic 工作区目前是空 `<section class="seismic-empty">`。
- **v1/v2 测试 + demo freeze 脚本** `scripts/freeze_demo_case.py` 存在。

**尚未存在（v3 待做）**：Intent Router 分支、IdeaBrief、SeismicDataAdapter、Novelty Checker、Baseline Discovery + Repository Verifier、Arena 竞技（排名/消融/Elo）、Code Experiment Loop（微观+宏观 ReAct）、Fair Comparison Planner、Result Evaluator、Ablation Agent、Hypothesis Switchback、Result Interpreter、v3 报告字段、v3 前端面板、v3 API 端点、地震 demo 数据。

## 3. 编排演进主线

LangGraph 图在 Sprint 间渐进生长，每 Sprint 有可演示增量：

```
S0(已完成): 线性 StateGraph（镜像 v1/v2）
S1: + intent_router conditional edge（三分支骨架）
S3: + 并行 Critic node + rank_hypotheses 排序 node + conditional_edges(by mode)
S4: + 微观 ReAct cyclic subgraph + 宏观 ReAct cyclic subgraph
S5: + evaluate_result → switchback/negative_result conditional edge
```

## 4. Sprint 详细设计

### S1 — 地基收尾 + Intent Router 分支（Layer 0）

**目的**：立起 v3 数据契约 + 第一个分支。没有 schema 后续 agent 无法传数据；没有 Intent Router 三模式分不开。

**产出**：
- `schemas/` 新增 v3 模型：`mode.py`(ResearchMode)、`idea.py`(IdeaBrief)、`baseline.py`(BaselineCandidate)、`arena.py`(HypothesisArenaResult + HypothesisArenaCandidate + PairwiseResult + EvolutionRecord + AblationChallenge)、`experiment.py` 扩展(ExperimentSpec/ExperimentRun/ResultCard/CodeDebugIteration/ExperimentIteration)。对应 PRD §11。
- `schemas/run.py`：`ResearchRun` 增 `mode/idea_brief/arena_result/baseline_candidates/experiment_runs/experiment_iterations/code_debug_log/seismic_data_profile` 等字段（带默认值，不破 v1/v2）。
- `langgraph_workflow.py`：`WorkflowState` 扩 `mode/arena_result/iteration/debug_iteration/messages`；图前部加 `intent_router` 节点 + `add_conditional_edges("intent_router", route_fn)`，按 `run.mode` 分到三条边（边后接 placeholder 节点，S3/S4/S6 填实）。
- 新增 `IntentRouterAgent`（LCEL）：输入用户文本 → `{mode, confidence, reason, required_inputs}`。新增 `IdeaIntakeAgent`：用户创意 → `IdeaBrief`。
- 新增 `SeismicDataAdapter` v1 + `data/seismic_demo/` 构造 subset（几百条，earthquake/explosion/noise）+ `experiments/seismic_event_classification/data/prepare_dataset.py`。
- 前端：`ResearchConsole` mode 选择接 `POST /api/runs` 的 `mode` 字段；按 mode 切换输入框（direction / idea / data_path+code_path）。

**验收**：三模式可路由到不同分支节点；地震问题生成结构化 `IdeaBrief`；v1/v2 tests 不破。

### S2 — 数据与 Baseline 发现层

**目的**：让系统能找到真实可复现 baseline 代码（v3 与 v1/v2 核心区别：baseline 优先来自文献+官方 GitHub，而非系统自编）；把地震数据 profile 做实。

**产出**：
- `SeismicDataAdapter` 补完：读事件元数据/波形、统计类别分布、检查采样率/窗口/通道完整性、生成 train/val/test split、标记类别不平衡与跨台站泛化风险。输出 PRD §6.3 profile JSON。
- `NoveltyCheckerAgent`（LCEL）：相似论文列表、是否有公开代码、方法重合点、可保留创新点、需降表述 claim、推荐优化方向。
- `BaselineDiscoveryAgent`：走 PRD §6.5 的 6 个 code source 通道（paper metadata code link / arXiv-PDF-作者主页 / Papers with Code / GitHub search / README matching / 用户手动提供）；每候选生成 `BaselineCandidate`。
- `RepositoryVerifier`（LCEL + 工具）：repo 存在/论文匹配/README/requirements/license/commit hash/IO；输出 `reproducibility_score/risks/run_command/safety`。
- Baseline repo 安全策略：clone 到 `data/external_baselines/{baseline_id}/` 隔离目录、命令白名单、写路径/网络限制、运行前后记 command/env/commit/dep/expected_outputs + stdout/stderr/exit/产物。
- 前端 `BaselineBoard`：baseline paper、repo URL、code_source、reproducibility_score、run status。
- 端点：`POST /baselines/discover`、`/baselines/{id}/verify-repo`（属 demo 子集之外的候选，看进度）。

**验收**：地震问题检索真实论文 + 发现带 code baseline + repo 可信度评分；未验证 repo 不进自动运行。

### S3 — Hypothesis Arena 竞技（Layer 1）

**目的**：把线性假设链（生成→批判→修订）升级为两种竞技。纯 LLM 推理层（成本低），与代码实验层（成本高）分离——只对 Top1 跑实验。

**产出**：
- Discovery 排名竞技：`HypothesisAgent` 生成 N=3~5 → 3 视角 Critic **并行**（Domain Scientist / ML-Experiment / Skeptical Reviewer）→ 8 维评分（novelty/verifiability/data_availability/feasibility/evidence_support/reproducibility/competition_fit/self_consistency）→ 加权排名 → Top1+Top2 进 Revision → 修订后再排名确认。
- Idea Refinement 消融式竞技：H_main vs H_challenge1~3（去创新点 A/B、用更简单替代）→ 输出创新点贡献/冗余判定 + `ablation_design`（不选「谁赢」，而是产出消融设计喂给 S5）。
- 多视角 Critic 用 LCEL 并行（三个独立 chain）。
- LangGraph：并行 Critic node + `rank_hypotheses` 排序 node + `add_conditional_edges("rank_hypotheses", route_by_mode)`；`arena_level=simplified_ranking`，Elo 字段（`elo_rating/pairwise_results/evolution_history`）先留 null。
- 前端 `HypothesisArenaPanel`：Discovery 排名表 / Idea Refinement 消融对比图 / Critic 雷达图。
- 端点：`GET /arena`、`POST /arena/run`（demo 子集候选）。

**验收**：两模式产出 `HypothesisArenaResult`；Top1 进实验、Top2 作 switchback 备选；Experiment Assistance 跳过竞技。

### S4 — Code Experiment Loop 双层 ReAct（Layer 2）

**目的**：搭受控地震分类实验框架，实现 PRD §6.9 双层 ReAct。v3 工作量最大、最区别于 v1/v2（v1/v2 实验只是文字计划 + 确定性 result card，无真实代码执行）。

**产出**：
- `experiments/seismic_event_classification/` 框架：configs（baseline_literature/proposed_fusion/ablation_*）、data（dataset/transforms）、models（baseline_adapter/cnn1d/spectrogram_cnn/fusion_net）、train.py/evaluate.py/run_ablation.py/result_card.py/README.md。
- 微观 ReAct cyclic subgraph：`generate/adapt_code → run_code → evaluate_error → fix_code → run_code`，max 5；局部修改约束（不整段重写，只改依赖/维度/配置/小结构）；每轮记 `CodeDebugIteration`（error_type/diagnosis/fix/code_diff/run_after_fix）；超限输出 `CodeDebugFailure` 进宏观诊断。
- 宏观 ReAct cyclic subgraph：`experiment → evaluate → diagnose → revise → experiment`，max 3；诊断分类（数据/模型/假设/复现）；每轮记 `ExperimentIteration`（reason/changes/previous_metrics/new_metrics/decision/human_approved）。
- `FairComparisonPlanner`：同 data/split/preprocessing/metrics/labels、报告参数量、数据泄漏检查。
- 受控执行：隔离目录、命令白名单、写路径/网络限制、运行前后记 command/working_dir/env/commit/dep/expected_outputs + stdout/stderr/exit/产物。
- 前端 `CodePlanPanel` / `CodeDebugPanel` / `ExperimentResultsPanel`。
- 端点：`POST /code-plan`、`/experiments/run`、`/experiments/debug`（demo 子集：至少 `/experiments/debug` 用于视频演示微观 ReAct）。

**验收**：≥1 baseline + ≥1 proposed 跑通；生成 accuracy/macro-F1/per-class F1/confusion + result card；微观调试有 diff；宏观迭代有 log；失败记 exit/错误/原因。

### S5 — Evaluator + Ablation + Switchback + v3 报告（Layer 3+4）

**目的**：给实验闭环装「判断+消融+回退+审计」，让报告诚实反映成败（失败写 negative result，不包装成功）。

**产出**：
- `ResultEvaluatorAgent`：pass/partial/fail 判据——proposed macro-F1 ≥ best baseline +1~2%、minority class F1 不降、目标类别混淆减少、消融关键模块正贡献、无明显泄漏。
- `AblationAgent`：PRD §8.2 消融矩阵——单通道vs三通道 / waveform vs spectrogram / 无融合vs融合 / 无attention / 无重采样 / 随机vs station-level split。消融设计来自 S3 Idea Refinement 的 `ablation_design`。
- Hypothesis Switchback（`add_conditional_edges("evaluate_result", ...)`）：Top1 不可修复→Top2（max 1 次）、切换后宏观 ReAct 重置计数、Idea Refinement 必须 `interrupt()` 用户确认、无备选→negative result。
- `ResultInterpreterAgent`：假设是否被支持、哪些证据/指标支持、哪些类别仍混淆、哪些只能写 preliminary、下一步建议。
- v3 报告字段（加进 `ReportWriterAgent` / `schemas/report.py`）：Baseline Provenance / Experiment Iteration Log / Code Debug Log / Hypothesis Arena Report / Ablation Report / Result Support Judgment。
- 前端 `FeedbackLoopPanel`；`ReportViewer` 显示 v3 新字段。
- 端点：`POST /experiments/ablation`、`/feedback/continue`、`/arena/switchback/{id}`、`GET /results`、`/result-card`（demo 子集：至少 `/arena/switchback` + `/feedback/continue` 用于视频演示）。

**验收**：proposed 不如 baseline 不包装成功；失败诊断（数据/模型/假设/复现）；switchback 切换；报告含全部新字段；最多 3 轮宏观迭代。

### S6 — 三模式闭环打通 + Experiment Assistance

**目的**：补第三种模式、三模式端到端联调、v3 API 收口（demo 子集）。

**产出**：
- Experiment Assistance 模式：`Code&DataAuditAgent`（理解代码结构、审计数据/实验配置、查泄漏/指标缺失/复现风险）→ S2 补缺失 baseline → S4 补跑 baseline/消融 → S5 ResultInterpreter → 报告。不竞技、不从零生成实验，只补全用户已有实验矩阵。
- 三模式端到端联调：修 S1–S5 接缝（Discovery Top1→S4、Idea Refinement ablation_design→S5、Experiment Assistance 跳过 Arena 直进 S4）。
- 前端三模式 input 差异化落地；Seismic Expert 工作区从空 section 填成完整面板布局。
- API：**demo 子集**——扩展 `GET /api/runs/{id}` 返回 v3 字段（arena_result/baseline_candidates/experiment_runs/code_debug_log/result_card/...），流程控制继续用 `/start` + `/continue`，仅额外加 S4/S5 标记的演示端点（`/experiments/debug`、`/arena/switchback`、`/feedback/continue`）。其余 20+ 端点看进度再补。

**验收**：三模式都能从前端入口跑到报告导出；Idea Refinement 模式可录屏演示完整闭环。

### S7 — Elo 升级 + Hardening + Demo Freeze

**目的**：MVP 简化版升级到 PRD 完整版、鲁棒性加固、冻结参赛 demo。

**产出**：
- Elo 竞技升级：新增 `LLMJudgeAgent`（pairwise 比较 + 分差）+ `EvolutionAgent`（针对性修改强者）。Discovery 完整 Elo（生成→Critic 初始化→pairwise→淘汰+进化→再对战→最终排名）；Idea Refinement 用 pairwise 分差判创新点贡献程度。`arena_level` 从 `simplified_ranking` 切 `elo_tournament`，**接口不变**（只改 Arena 内部），前端按 `arena_level` 切换排名表/对战矩阵。
- Hardening：
  - 真实公开小数据集接入（Claude 帮选 + 写 `SeismicDataAdapter`；候选方向 STEAD subset / IRIS FDSN+USGS-ComCat 目录 / 经典教学判别集；S7 先核实可下载性、标签覆盖、体量小，再接；看开发进度决定是否做）。
  - baseline repo cache（不重复 clone）、dependency resolution report、workspace bundle export + 重启恢复 run state、`ClaimVerifier` 升级为 Qwen/embedding 语义核验（替换词汇匹配）。
- Demo Freeze：固定 input / baseline paper+repo / dataset subset / result card / final report；前端截图、10 分钟视频脚本、技术方案 PDF（≤20 页，PRD §13 目录）、Qwen 调用日志截图。复用并扩展 `scripts/freeze_demo_case.py`。

**验收**：新环境按 README 跑通地震分类 demo；报告含 Baseline Provenance/Citation Audit/Claim Audit/Ablation/Iteration Log；10 分钟视频展示 Idea Refinement 完整闭环（竞技矩阵 + 代码调试 + 假设回退）。

## 5. 依赖与并行

- S1 是硬前置（schema + 分支骨架）。
- S2（Baseline）与 S3（Arena）在 S1 后可部分并行（不同 agent 集、不同人）。
- S4 依赖 S2（baseline）+ S3（Top1 假设）。
- S5 依赖 S4。
- S6 依赖 S5；S7 依赖 S6。
- 每 Sprint 内前端面板与后端可并行。

## 6. 风险与应对

| 风险 | 应对 |
|---|---|
| 范围仍偏大，1–2 个月做不完完整 v3 | S6 API/S7 数据集已设弹性开关（先 demo 子集/构造 subset，看进度再扩）；如超时优先保 Idea Refinement 闭环可录屏 |
| LangGraph cyclic subgraph 调试复杂 | 微观/宏观 ReAct 先手写 while 跑通，再迁 LangGraph cyclic（与 PRD §14.1「先跑通再换编排」一致） |
| 外部 baseline 代码不可复现 | Tier 分层 + reproduction_status + fallback 通用 baseline（PRD §6.5/§15） |
| 真实公开数据集下载/标签不稳 | 开发期用构造 subset 不卡住；S7 先核实再接，接不上则继续构造 subset + 在报告标注数据来源 |
| LLM 生成代码不可控 | 受控框架 + 配置/局部模块生成 + 每次 logs/result card + 不信任未运行代码（PRD §15） |

## 7. 与 PRD_v3 Sprint 的映射

| 原 PRD Sprint | 重排后 |
|---|---|
| V3-1 模式入口+地震 domain | S1（含 LangGraph 骨架收尾，原 V3-1 不再单独做 LangGraph 迁移） |
| V3-2 Baseline Discovery | S2（+ SeismicDataAdapter + Novelty Checker） |
| （原计划散在 V3-1 的竞技） | S3 独立成 Sprint |
| V3-3 Code Experiment Loop | S4 |
| V3-4 Feedback Loop + 消融 | S5（+ Switchback + v3 报告字段） |
| V3-5 Demo Freeze | S7（+ Elo 升级 + Hardening） |
| V3-6 Hardening | S7 |
| （原计划未单列） | S6 三模式打通 + Experiment Assistance + API 收口 |
