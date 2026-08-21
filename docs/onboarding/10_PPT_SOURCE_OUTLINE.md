# 后续 PPT 页级素材提纲

> 这是内容提纲，不是最终 PPT。建议 14 页，展示时控制在 8–10 分钟。

| 页 | 主题与目的 | 建议要点 | 推荐素材 | 来源 |
|---:|---|---|---|---|
| 1 | 封面 | 项目名、赛题、团队、版本日期 | 当前完整 16 页版封面风格 | `项目展示/` 正式 PPT |
| 2 | 问题与痛点 | 科研信息碎片化；大模型幻觉；实验与证据脱节 | “普通问答 vs 可审计科研闭环”对比 | `PRD_v3.md`、状态文档 |
| 3 | 项目定位 | 多智能体 AI Scientist；本地优先；可信证据链 | 一句话定位 + 三个差异点 | `docs/onboarding/README.md` |
| 4 | 总体架构 | frontend、backend、browser-worker、Qwen、存储、实验 | 六层架构图 | `02_ARCHITECTURE.md` |
| 5 | 三种研究入口 | discovery、idea_refinement、experiment_assistance | 三列输入/处理/输出对比 | `03_RUNTIME_FLOW.md`、`04_INPUT_OUTPUT.md` |
| 6 | 多智能体科研链 | 规划、文献、证据、假设、实验、报告 | agent 分工时间线 | `05_MODELS_ALGORITHMS.md` |
| 7 | 可信文献与证据 | DOI/标题核验、Evidence Ledger、人工冻结、Claim Audit | 文献板/证据板/审计截图 | `02_ARCHITECTURE.md`、正式界面截图 |
| 8 | 假设竞技与反馈 | 多视角批判、challenger、novelty、重搜 | Arena 矩阵与循环箭头 | `03_RUNTIME_FLOW.md` |
| 9 | baseline 与实验闭环 | baseline provenance、固定 harness、model.py、安全检查 | baseline 面板、代码计划、调试面板 | `05_MODELS_ALGORITHMS.md`、界面预览 |
| 10 | 输入与输出 | 问题/模式/指标/代码；报告/证据/工作区/PDF | 输入输出表和报告截图 | `04_INPUT_OUTPUT.md` |
| 11 | 算法与模型 | Qwen、LCEL、LangGraph、LR baseline、生成 sklearn 模型 | 分层技术栈 | `05_MODELS_ALGORITHMS.md` |
| 12 | 已有验证结果 | 279 后端测试、22 前端测试、构建通过、harness 指标 | 验证表与 baseline=method 柱状图 | `06_RESULTS_EVIDENCE.md` |
| 13 | 可信边界与不足 | 合成数据、无预训练权重、fallback、非 OS 级 sandbox | “已验证/不能证明”双栏 | `01_PROJECT_STATUS.md`、`06_RESULTS_EVIDENCE.md` |
| 14 | 完成度与路线图 | 主体闭环完成；真实数据与正式复现是下一阶段 | P0/P1/P2 路线和两人分工 | `09_NEXT_WORK.md` |

## 每页可直接使用的核心句

1. **定位**：TrustSci-Agent 把大模型推理放进可核验、可恢复、可导出的科研工作流，而不是只生成一段看似专业的答案。
2. **证据**：文献候选、引用核验、证据条目、报告主张和人工决定在同一个 run 中关联。
3. **实验**：模型只能改 `SeismicModel`，数据、baseline、测试、指标和运行脚本由系统固定。
4. **结果**：测试通过、超过 baseline、科学主张成立是三种不同判断。
5. **边界**：当前地震结果来自合成波形，展示的是软件科研闭环，不是实际地震分类性能。
6. **进度**：当前代码通过 279 项后端测试、22 项前端测试和生产构建，下一阶段重点是真实数据与独立复现。

## 推荐截图

- 系统入口与任务配置。
- 三栏科研工作台总览。
- 文献与论文阅读。
- 引用与证据账本。
- 假设竞技与可信 baseline。
- 实验计划、代码调试和结果。
- 报告审计与工作区导出。

优先使用 `项目展示/成品预览_完整16页/` 中已经正式交付的图片。不要使用 `.pptx-build/`、早期预览或包含临时错误状态的截图。

## 答辩时应避免的表述

- 不说“系统已在真实地震数据上达到 83.33%”。
- 不说“所有引用都由 AI 自动证明真实可靠”。
- 不说“可以安全执行任何外部代码”。
- 不把 fallback 输出当作 Qwen 在线推理结果。
- 不把本机 470 条保存状态说成 470 次科研实验。

## 制作前最后核对

PPT 中的测试数量、模型名、数据集、指标和完成状态必须以制作当天的 [项目状态](01_PROJECT_STATUS.md) 与 [结果证据](06_RESULTS_EVIDENCE.md) 为准；如重新运行了真实案例，应替换本提纲中的旧数字并保留验证日期。

