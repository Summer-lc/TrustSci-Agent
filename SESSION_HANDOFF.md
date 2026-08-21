# Session Handoff — TrustSci-Agent v3 开发接续

> 新窗口/Claude 会话开新会话时,先读本文件 + `prd_v3_sprint.md`(总 Sprint 设计)+ 对应 `prd_v3_sN_plan.md`,即可无缝接续。最后更新:2026-07-03。

## 1. 项目 & 环境

- **项目**:TrustSci-Agent,基于阿里云百炼 Qwen 的多智能体 AI Scientist 系统,挑战杯参赛。仓库:`d:/For work/TrustSci-Agent`。
- **设计文档**(仓库根):
  - `PRD_v1.md` / `PRD_v2.md` / `PRD_v3.md` — 产品需求(v3 是地震竞技版,最新)。
  - `prd_v3_sprint.md` — v3 的 7-Sprint 重排设计(S1–S7),**总纲**。
  - `prd_v3_s1_plan.md` / `prd_v3_s2_plan.md` / `prd_v3_s3_plan.md` / `prd_v3_s35_plan.md` / `prd_v3_s4_plan.md` / `prd_v3_s5_plan.md` — 已完成 sprint 的逐 Task 实施计划。
- **运行**:Docker dev 栈(热重载)。启动:`make dev`(或 `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`)。前端 http://localhost:3000,后端 http://localhost:8000。
  - `WORKFLOW_ENGINE=langgraph`(用户跑的是 LangGraph 引擎,不是 classic)。
  - 真实 Qwen:`DASHSCOPE_API_KEY` 已配,模型 `qwen3.7-max`(推理模型,planner ~75s)。
  - GitHub 无 token(匿名 60/hr);Papers with Code 从容器连不上(超时,优雅降级)。
- **测试**:`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m pytest -q`(当前 216 passed, 0 failed, 2026-07-03 实跑;S4+S5 加了 ~70 个测试)。
- **执行方式**:subagent 驱动(superpowers:subagent-driven-development),**不 commit**(用户要求所有改动留本地工作区)。task-brief 脚本:`bash "C:/Users/坐标/.claude/plugins/cache/claude-plugins-official/superpowers/6.0.3/skills/subagent-driven-development/scripts/task-brief" <plan_file> <N>`。
- **进度 ledger**:`.superpowers/sdd/progress.md`(S1/S4 记录完整;S2/S3/S3.5 未补记)。

## 2. 已完成(S1 → S5)

- **S1 地基 + Intent Router**:`ResearchMode`/`IdeaBrief`/`SeismicDataProfile` schema;`IntentRouterAgent`/`IdeaIntakeAgent`(LCEL);`SeismicDataAdapter` + 构造 demo subset(`data/seismic_demo/events.csv`,120 合成事件,**无真实波形**);LangGraph `intent_router` conditional edge + 三分支 placeholder;API 透传 `mode`;前端 Mode Selector 接通。
- **S2 Baseline 发现层**:`BaselineCandidate` schema;`GithubBaselineClient`/`PapersWithCodeClient`(httpx,可降级);`NoveltyCheckerAgent`/`BaselineDiscoveryAgent`/`RepositoryVerifierAgent`(LCEL + GitHub);discover/verify-repo 端点;前端 `BaselineBoard` + `SeismicOverviewPanel`。
  - S2 live fix:GitHub 宽查询(短查询才返回结果)、Seismic 侧栏 console、CSS、隐藏 arXiv/Semantic Scholar 开关。
- **S3 Arena 竞技 + Baseline 自动化**:把 S2 的按需按钮改成**自动 graph 节点**(seismic 专属,无人工 gate);`CriticArenaAgent`(3 视角并行 LCEL)、`ChallengerAgent`、`HypothesisArenaAgent`(Discovery 排名 + Idea Refinement 消融式,自动选 Top1);`code_url_extractor`(摘要 + PDF 正文挖 github 链接);LangGraph seismic 链:`... → arena → extract_code_urls → baseline_discover → baseline_verify → experiment_design`;前端 `HypothesisArenaPanel`。
- **S3.5 Baseline Quality Gate**(基线质量门):
  - `PaperTypeClassifier`(LCEL):每篇论文标 `paper_role`(method_model/dataset_benchmark/survey_review/...),只有 method_model `baseline_eligible`。
  - `RepositoryVerifier` 增强:判 `repo_type`(model_code/dataset_only/...)+ `is_model_baseline`;dataset-only repo 不能 verified。
  - `BaselineDiscovery`:只用 eligible 论文;**关掉 task 级宽搜**;`code_url_source` 记真来源(修了 paper_pdf 标签 bug);`stars`;初始 `baseline_priority_score`。
  - 按 `baseline_priority_score` 排序验证 top-3;`paper_classification` step(seismic,literature_mining 之后)。
  - **相关性预过滤**(正:seismic/earthquake/waveform/EQTransformer/STEAD...;负:covid/nlp/recommender/lung...)— GitHub 搜结果过滤,paper-code 候选不过滤。
  - 前端 LiteratureBoard 显 paper_role;BaselineBoard 显 repo_type/priority/rejection。
  - **重搜循环留 S5**(未做):过滤后 0 baseline 时不重搜,诚实输出"baseline 不足"。
- **S4 Code Experiment Loop**(代码实验闭环,2026-07-02 完成):把 Arena Top1 假设真写成代码跑起来。固定 harness(`experiments/seismic_event_classification/`:`data.py` numpy 合成波形 120×3×3000 unit-RMS sines+noise + `baseline.py` 弱基线时域统计+LR + `train.py`/`tests.py` + `harness_manifest.json`)+ LLM 只写 `model.py`(`CodeWriterAgent` LCEL,`response_format=text`,骨架 fallback 防失智)+ `SandboxExecutor`(同容器 subprocess,白名单 tests.py/train.py,timeout)+ micro ReAct(写→tests→修 max 3,**无 macro**,tests 不过 skip train,train 崩直接 failed)+ `FairComparisonPlanner`(确定性无 LLM)+ `code_experiment` LangGraph 节点(seismic 真跑,非 seismic no-op,`experiment_design→code_experiment→report_writer`)+ 新 `CodeExperimentResult` schema(结构化 summary,acceptance_gate 与 comparison.outcome 分开)+ 前端 `CodePlanPanel`(折叠 model.py)/`CodeDebugPanel`/`ExperimentResultsPanel`。live 验证:真实 Qwen 一轮写出 spectral-FFT RandomForest,method accuracy 1.0 vs baseline 0.833,`completed_positive`。计划:`prd_v3_s4_plan.md`。**真实 STEAD 数据集接入选 S7**;macro ReAct/switchback/baseline 重搜留 S5。已知小尾巴(Minor,留 S5/S7):`ExperimentResultsPanel` 未渲染 per_class_f1;`data.load_split` 每次重算波形(120 事件可忽略,S7 放大时再看)。
- **S5 统一反馈循环**(2026-07-03 完成):三循环 + dirty-flag 依赖感知重跑。(A) `novelty_check`(arena 后,扩 NoveltyCheckerAgent 5 verdict: novel/transfer_applicability/already_done/dataset_only/similar_work;already_done→Arena 重生成注入 avoid_prior_art 防 loop,cap 2→low_novelty 继续;transfer/similar→RevisionAgent 收窄 claim;prior_art 论文 dual-effect 进 baseline 候选)。(B) `baseline_quality_gate`(baseline_verify 后,两层门:运行门 harness_trivial 兜底恒过 + 科研门 ≥1 verified_repo;fail→re_search cap 2 聚焦查询替换 dataset/no-code 论文;dep-aware: evidence_changed→全链重跑 evidence_ledger→...→baseline_quality_gate,否则只 baseline_discover+verify;cap 仍 0→comparison_grade=degraded 降级运行门)。(C) `macro_react`(code_experiment 后,触发: failed OR completed_negative margin≥0.05;macro cap 1 全局(Top2 不享 macro)+ switchback Top2 fresh-only 无 Top3;窄负<0.05 接受;决策/路由分离: _run_macro_react 设 code_experiment_mode+计数器, _route_after_macro honoring mode)。inner cap 不重置防嵌套爆炸。classic `_run_after_evidence_review` 线性透传 3 新 step 无 cycle,完整循环仅 LangGraph。顺手修了 S3.5 遗留 `per_source_limit=max(max_papers+2,8)`。前端 `FeedbackLoopPanel`(verdict/grade/rounds/dirty flags)。live 验证:真实 Qwen novelty 正确判 similar_work+提 claim_revision;macro cycle 把 failed 实验修成 completed_positive。计划:`prd_v3_s5_plan.md`。**§5.4 报告增强(Result Evaluator/Ablation Agent/Result Interpreter/v3 报告 provenance 字段)拆到 S5.5/S6**。

## 3. 关键设计决策(用户拍板,别推翻)

- **编排基于 LangChain 生态**:agent 走 LCEL(`LLMClientRunnable` + `build_agent_prompt` + `FallbackParser`,仍调 `QwenClient.complete()`,审计日志在 `data/outputs/llm_calls/{run_id}.jsonl`);工具走 LangChain Tool;分支/循环/回退走 LangGraph StateGraph。`LangGraphWorkflow` 继承 `ScientistWorkflow`(共享 step 方法 + 图节点 wrap)。
- **全自动,无人工 gate**(用户要求):Arena 自动选 Top1,不 `interrupt()`。switchback(S5)也自动。
- **demo 数据是合成的**:`data/seismic_demo/events.csv` 是构造元数据,无真实波形。真实公开小数据集(STEAD 子集等)接入选 S7(用户:开发期用构造 subset,看进度接真实集)。
- **S6 API 先做 demo 子集**(扩展 `GET /api/runs/{id}` + 仅演示端点),看进度再补全 20+ 端点。
- **不 commit**(用户:所有改动本地)。
- **YAGNI**:schema/字段按所属 sprint 创建,不提前建。

## 4. 已知问题 / 待办(非 bug,留给后续)

- **✅ 测试全绿(216 passed, 0 failed, 2026-07-03 实跑确认)**。此前那条失败的 `tests/test_literature_router.py::test_literature_router_ranks_seismic_papers_above_generic_cross_domain_results` 已被 ChatGPT 的 domain-aware 排序修好(seismic 扩展查询后该测试只走 1 个源 → `per_source_limit=4` 拿全 4 篇,`_rank_seismic_results` 给出 `[seismic_detection(22), blast(18), volcanic_ash(-4), medical(-8)]`,`papers[:2]==[seismic_detection, blast]` ✓)。
- **✅ S3.5 遗留 `per_source_limit` 截断坑已修(S5 Task 3)**:`literature_router.py:54` 改为 `per_source_limit = max(max_papers + 2, 8)`(取更大候选池再排名),现有 literature_router 测试不破。
- **ChatGPT 在 S3.5 之后又做了一轮改动(已合入工作区,216 passed / 0 failed)**,新窗口需知晓:
  - 前端 `ResearchConsole`:seismic 模式删了"研究领域"下拉框(强制 `domain=seismic_event_classification`,避免旧状态带偏);classic 保留。seismic 默认问题改清楚(四分类只是例子)。Semantic Scholar/arXiv 开关改成 `<div hidden>`(仍受控但 UI 隐藏)。
  - `PlannerAgent`:加了地震专用 fallback plan `_seismic_fallback_plan` + 5 个 seismic perspectives(不再 fallback 到固态电解质);SYSTEM_PROMPT 也加了 seismic 查询约束段。
  - `LiteratureRouter.search` **新增 `domain` kw-only 参数**:domain=seismic 时注入 4 条 `_SEISMIC_PRIORITY_QUERIES` 扩展查询、`query_limit=4`、用 `_rank_seismic_results`(anchor/strong-phrase/method/negative 四级打分,把 CT/医学/火山灰/推荐系统/COVID 等噪声压到队尾)。调用点 `scientist_workflow.py:_search_literature` 传 `domain=run.domain`(LangGraph 复用同方法,一条路径覆盖)。
  - `PaperTypeClassifierAgent` **重写 eligibility 逻辑**:新增 `Paper.seismic_relevant` 字段;`baseline_eligible = method_model AND seismic_relevant`(s35 原版只要 method_model,更严)。新增 `_is_seismic_relevant` 本地启发式(正/负词表),在 `_normalize` 用 `seismic_relevant = llm_result and _is_seismic_relevant(p)` 做**本地 guardrail 覆盖 LLM**——即使 LLM 把 generic ML 论文标成 seismic_relevant,本地词表也能否决。SYSTEM_PROMPT 要求 LLM 输出 `seismic_relevant`。前端 `api.ts` 同步了该字段。
  - 这些改动**与 S4 兼容**(S4 是代码实验,不碰文献),且**有利于 S5**(S5 重搜循环可直接复用 domain-aware 检索 + 已内置的地震去噪,不用再造)。
- `BaselineCandidate` 不存 paper_role(故 post-verify `baseline_priority_score` 用 repo 侧信号)。
- paper-code 候选的 `repo_type` 用 repo 名启发式(粗)。
- PaperTypeClassifier / repo_type 判定靠 LLM,有误判;前端标 reason 供人工核。
- PwC 通道连不上(容器网络),只靠 GitHub。
- baseline 发现在论文没自声明 code + per-paper 搜不到 seismic repo 时会 0 候选 → S5 重搜循环解决。
- 前端 Seismic 工作区目前面板:SeismicOverviewPanel / HypothesisArenaPanel / LiteratureBoard / BaselineBoard / WorkspacePanel。S2 的「发现 Baseline」/「Verify Repo」按钮仍在(baseline 现已自动跑,按钮用于手动重跑)。

## 5. 下一步:S6(S5 已完成)

- **S5 = 统一反馈循环 ✅(2026-07-03 完成)**:三循环(novelty_check / baseline_quality_gate 两层门+dep-aware 重搜 / macro_react+switchback)+ dirty-flag 依赖感知重跑 + inner cap 不重置。live 验证:真实 Qwen novelty 判 similar_work+提 claim_revision;macro cycle 把 failed 实验修成 completed_positive。详见 §2 + `prd_v3_s5_plan.md`。S5 留给后续的钩子:`ResearchRun.novelty_verdict`/`baseline_gate_status`/loop 计数器(comparison_grade=research|degraded);`code_experiment_mode`/`macro_round`/`switchback_used`;§5.4 报告增强(Result Evaluator/Ablation Agent/Result Interpreter/v3 报告 provenance 字段)拆到 S5.5/S6;`verified_repo` baseline 分支(S7 接真实 STEAD+真实 repo 验证后才常触 research grade)。
- **S6 = 三模式打通 + Experiment Assistance + API 收口 + §5.4 报告增强**:
  1. **三模式打通**:discovery(已完成 seismic 链)+ idea_refinement(已有 Arena 消融式)+ experiment_assistance(S6 新做,用户上传已有实验结果/代码,系统协助分析/对比/写报告,不重新跑 S4 闭环)。
  2. **API 收口**:扩展 `GET /api/runs/{id}` 返回完整 v3 状态(含 `code_experiment`/`novelty_verdict`/`baseline_gate_status`/loop 计数器);补 demo 演示端点(用户:先做 demo 子集,看进度再补全 20+ 端点)。
  3. **§5.4 报告增强**:Result Evaluator(pass/partial/fail)、Ablation Agent、Result Interpreter、v3 报告 provenance 字段(Baseline Provenance / Experiment Iteration Log / Code Debug Log / Arena Report / Ablation Report / Result Support Judgment)扩进 `SystemProvenance`。前端 Feedback Loop Panel(S5 已做)。
  - S6 计划还没写(用 brainstorming + writing-plans 出 `prd_v3_s6_plan.md`)。
- 之后:S7(Elo 升级 + Hardening + 真实数据集 STEAD + Demo Freeze)。

## 6. 给新窗口的开场指令(可直接粘贴)

```
我们在做 TrustSci-Agent(挑战杯 v3 地震竞技版)。先读仓库根的 SESSION_HANDOFF.md 和 prd_v3_sprint.md 了解全貌和进度。S1/S2/S3/S3.5/S4/S5 已完成(216 测试过),下一步是 S6(三模式打通 + Experiment Assistance + API 收口 + §5.4 报告增强)。

环境:Docker dev 栈已跑(WORKFLOW_ENGINE=langgraph,真实 Qwen),前端 :3000 后端 :8000。改动不 commit,留本地。用 subagent 驱动执行(task-brief 脚本见 handoff)。

我们在做 TrustSci-Agent(挑战杯 v3 地震竞技版)。先读仓库根的 SESSION_HANDOFF.md 和 prd_v3_sprint.md 了解全貌和进度。S1/S2/S3/S3.5/S4/S5 已完成(216 测试过),下一步是 S6(三模式打通 + Experiment Assistance + API 收口 + §5.4 报告增强)。

环境:Docker dev 栈已跑(WORKFLOW_ENGINE=langgraph,真实 Qwen),前端 :3000 后端 :8000。改动不 commit,留本地。用 subagent 驱动执行(task-brief 脚本见 handoff)。

现在我想开始 S6。先用 brainstorming + writing-plans 出 prd_v3_s6_plan.md。S6 = (1) 三模式打通(experiment_assistance 新做:用户上传已有实验/代码,系统协助分析对比写报告,不重跑 S4 闭环);(2) API 收口(扩展 GET /api/runs/{id} 返回完整 v3 状态含 code_experiment/novelty_verdict/baseline_gate_status/loop 计数器 + demo 演示端点);(3) §5.4 报告增强(Result Evaluator/Ablation Agent/Result Interpreter/v3 报告 provenance 字段扩进 SystemProvenance)。全自动无 gate。依赖 S4+S5 产出。开始吧。
```

(如果不想马上 S6,把最后一句换成你想做的事即可。)

## 2026-07-06 S6 本地完成记录

- 已恢复 Windows Python 3.11 虚拟环境并固定核心依赖版本，避免 pip 依赖回溯卡死。
- 已恢复 `.env.example`，新增 `scripts/check_dev_env.py`。
- 三模式已形成行为分流；`experiment_assistance` 不执行用户提交代码，直接生成结果评价、消融分析、结果解释与报告。
- 新增 `POST /api/runs/{id}/experiment-assistance` 与 `GET /api/runs/{id}/v3-summary`。
- 报告 provenance 已扩展 Arena、Baseline、实验迭代、调试、消融与结果支持判断。
- 生成的 `model.py` 在执行前经过 AST 拒绝策略检查，并通过隔离解释器参数运行固定 harness。
- 前端新增实验辅助输入和结果分析面板。
- 2026-07-06 新鲜验证：`233 passed, 3 warnings`；Next.js 生产构建通过；无 Key 端到端实验辅助运行完成且报告生成成功。
- Docker CLI 在当前 Windows shell 不可用，因此未进行 Docker Compose 验收。
- 所有修改按用户要求留在本地工作区，未 commit。
