# 输入、输出与数据格式

## 1. 创建研究任务

最小输入：

```json
{
  "domain": "seismic_event_classification",
  "question": "如何利用多通道波形改进地震事件分类？",
  "mode": "discovery",
  "constraints": {
    "must_verify_citations": true,
    "max_papers": 6,
    "require_experiment_plan": true,
    "enable_browser_worker": false,
    "enable_semantic_scholar": false,
    "enable_arxiv": true,
    "workflow_mode": "auto"
  }
}
```

`domain` 常用值：`seismic_event_classification`、`energy_materials`。`mode` 为 discovery、idea_refinement、experiment_assistance。

## 2. baseline 输入

任务启动前可选择：

- `manual_upload`：名称、说明、代码文本或仓库地址、运行命令、数据描述、指标和备注。
- `ai_generated`：使用固定本地演示 baseline，信任级别为 runnable_demo。
- `none`：明确无可信 baseline，报告必须降级说明。

示例：

```json
{
  "strategy": "manual_upload",
  "manual": {
    "name": "团队现有 CNN baseline",
    "dataset_description": "内部划分，仅用于本次分析",
    "metrics": [
      {"name": "macro_f1", "value": 0.74, "split": "test"}
    ],
    "notes": "指标由用户提供，系统未独立复现"
  }
}
```

用户代码不会因为被粘贴为 manual baseline 就自动执行。

## 3. experiment_assistance 输入

必填：objective、method_summary；并且至少提供一项方法指标或一条实验日志。可选 source_code、dataset_description、baseline 指标、消融结果和作者备注。

```json
{
  "objective": "比较新模型与现有 baseline",
  "method_summary": "融合时域与频域特征",
  "dataset_description": "用户提供的数据划分",
  "baseline_name": "CNN baseline",
  "baseline_metrics": [{"name": "macro_f1", "value": 0.74}],
  "method_metrics": [{"name": "macro_f1", "value": 0.78}],
  "ablations": [],
  "logs": ["训练完成，无崩溃"],
  "author_notes": "系统仅分析，不重新执行提交代码"
}
```

## 4. 外部输入源

| 类型 | 来源 | 是否必须联网 | 可信边界 |
|---|---|---:|---|
| 论文元数据 | OpenAlex、Crossref、Semantic Scholar、arXiv | 是 | 元数据可核验，结论仍需阅读原文 |
| 网页/PDF | browser-worker、PDF parser | 是/本地 | 抓取成功不改变引用状态 |
| 材料数据 | 本地 CSV、可选 Materials Project | 可选 | 样例数据不代表实验数据库完整接入 |
| 地震数据 | `events.csv` + NumPy 合成波形 | 否 | 仅软件验证，不是真实观测波形 |
| baseline | 用户提供、AI 演示、候选仓库 | 视策略 | 必须标记 provenance 与 trust level |
| Qwen | 百炼兼容 API | 是 | 无 Key 时为 fallback |

## 5. `ResearchRun` 中间状态

运行对象聚合：意图、计划、多视角问题、论文、引用报告、PDF chunks、证据、知识卡、数据 profile、候选 baseline、假设、Arena、新颖性、实验计划、代码实验、结果评价、消融、解释、报告、步骤、错误、信任警告和控制动作。

关键状态值：created、running、paused、completed、failed、abandoned。原子步骤还记录 attempts、error_code、retryable、skippable 和事件历史。

## 6. 本地工作区产物

典型目录：

```text
data/workspace/run_xxx/
├── run.json
├── research-state.json
├── research-log.md
├── papers/papers.json
├── evidence/evidence.json
├── evidence/knowledge-cards.json
├── hypotheses/hypotheses.json
├── experiments/experiment-plan.json
├── reports/report.json
└── to_human/next-actions.md
```

自动代码实验还会产生模型源码、迭代/调试记录、metrics 和 comparison。具体路径由 `workspace_artifacts` 记录。

## 7. 最终输出

- 完整 `ResearchRun` JSON 与 V3 summary。
- 论文、证据、知识卡、数据 profile、baseline、假设和 claim audit API。
- 中英文结构化研究报告。
- Markdown、JSON、PDF 报告导出。
- workspace ZIP 导出与 restore。
- Qwen 调用审计日志（本地保留）。
- 浏览器截图或 metadata-only 论文预览。

## 8. 输出解读规则

- `completed` 表示软件流程结束，不自动表示科学结论成立。
- `completed_positive` 表示当前固定比较中方法指标高于 baseline，不表示真实数据外推成立。
- `completed_negative` 仍是有效实验结果，不应隐藏。
- experiment_assistance 的结果是对用户提供信息的分析，不是系统独立复现实验。
- `comparison_grade=degraded` 表示可信 baseline 不足，报告应限制主张。

完整接口列表见 [API 文档](../API.md)。

