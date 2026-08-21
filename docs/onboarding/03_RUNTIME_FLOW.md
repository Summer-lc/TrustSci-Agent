# 代码运行流程

## 1. 从页面到运行对象

1. `frontend/components/workbench/ResearchConsole.tsx` 收集版本、研究模式、问题和约束。
2. `Workbench.tsx` 通过 `frontend/lib/api.ts` 调用 `POST /api/runs`。
3. `routes_runs.py` 创建 `ResearchRun`，生成 `run_id` 和显示名称，保存初始状态。
4. 如果选择 baseline 或 experiment_assistance，前端在启动前分别调用 baseline-intake 或 experiment-assistance 接口。
5. `POST /api/runs/{run_id}/start` 后台启动工作流；`run-sync` 用于同步测试/调试。
6. 前端轮询 `GET /api/runs/{run_id}`，把原子步骤映射为阶段和对话消息。

## 2. 三种研究模式

| 模式 | 适用输入 | 主要差异 |
|---|---|---|
| `discovery` | 一个待探索的科研问题 | 系统生成候选假设并选择可验证方向 |
| `idea_refinement` | 用户已有初步想法 | 重点批判、收窄主张和比较候选 |
| `experiment_assistance` | 用户已有方法、指标、日志或代码文本 | 不执行用户代码，直接评估结果、消融和限制 |

LangGraph 在 `intent_router` 后进入三个模式节点，再共享计划、文献和证据流程。模式差异主要在意图解析、Arena 行为和数据 profile 后的路由。

## 3. LangGraph 主链

```text
START
  → entry（新任务或恢复入口）
  → intent_router
  → branch_discovery | branch_idea_refinement | branch_experiment_assistance
  → planner
  → literature_search
  → citation_verification
  → [guided: pause_citation]
  → evidence_ledger
  → literature_mining
  → [guided: pause_evidence]
  → paper_classification
  → scientific_data_profile
```

之后按模式/领域分支：

- experiment_assistance：直接进入 `result_evaluation`，不执行用户代码。
- seismic discovery/idea_refinement：进入 Arena、baseline、实验与反馈链。
- classic/非地震：进入假设评审和实验设计；代码实验节点会按领域决定是否 no-op。

## 4. 地震假设与 baseline 链

```text
arena
  → novelty_check
      ├─ already_done 且未达轮次上限 → arena
      └─ 继续 → baseline_intake
  → baseline_quality_gate
      ├─ 证据不足且未达轮次上限 → re_search_literature
      │     ├─ evidence_changed → evidence_ledger（重建下游）
      │     └─ 否则 → baseline_intake
      └─ 通过/降级 → experiment_design
```

当前主信任路径要求先选择 baseline 策略：用户提供、AI 生成本地演示 baseline 或无 baseline。自动发现和仓库验证代码仍可用于候选研究和手动调试，但不能把未经验证的 GitHub 仓库直接当作可信执行基线。

## 5. 代码实验与结果反馈

```text
experiment_design
  → code_experiment
      → 生成 model.py
      → AST 安全检查
      → tests.py（接口与预测有效性）
      → 失败时有限次代码修复
      → train.py
      → metrics.json + comparison.json
  → experiment_result_gate
      ├─ 明显失败/负结果且未达上限 → experiment_redesign → code_experiment
      └─ 接受结果 → result_evaluation
  → ablation_analysis
  → result_interpretation
```

“代码修复”处理导入、接口、预测等实现错误；“实验重设计”处理方法在科学比较中明显表现不佳。两者不能混为同一种 retry。

## 6. 报告与审计

```text
result_interpretation
  → report_writer
  → claim_verification
  → report_revision
  → claim_reverification
  → report_translation
  → finalize
  → END
```

报告包含中英文研究报告以及系统 provenance：工作流、证据账本、引用审计、主张审计、Arena、baseline 来源、实验迭代、调试、消融和结果支持判断。API 支持 Markdown、JSON、PDF 导出以及完整工作区压缩包。

## 7. 人在回路

`ResearchConstraints.workflow_mode`：

- `auto`：自动继续。
- `guided`：引用核验后与证据提炼后暂停；用户完成 accept/reject 和 freeze 后调用 `continue`。

冻结不是删除：论文或证据的人工决定、冻结列表和审计状态都保存在 `ResearchRun` 和工作区。

## 8. 错误、重试和恢复

- 瞬时网络、限流、模型或浏览器错误自动重试一次。
- 再次失败，或确定性输入/校验错误，步骤进入 `waiting_action`。
- 前端只显示后端允许的 retry/skip；关键 baseline、实验结果和报告步骤不能静默跳过。
- 用户可 pause/resume/abandon 运行；abandoned 是终态。
- `recover` 用于用户主动选择的历史任务：孤立 running 步骤转为可处理状态，已完成成果不重跑。
- 每次动作写入 `last_action`、事件列表和恢复计数。

## 9. 持久化时机

任务创建、原子步骤变化、用户控制、最终完成和异常都会更新 run store 与 `data/workspace/run_*`。因此前端刷新或进程重启后可从工作区恢复，但原始本地工作区默认不进入 GitHub。
