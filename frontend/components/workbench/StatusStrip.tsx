import { Activity, Database, Server } from "lucide-react";
import { PublicConfig, ResearchRun } from "../../lib/api";

export function StatusStrip({ config, run }: { config: PublicConfig | null; run: ResearchRun | null }) {
  const semanticEnabled = run?.constraints.enable_semantic_scholar || (!run && config?.semantic_scholar_configured);
  const arxivEnabled = run?.constraints.enable_arxiv ?? true;
  const literatureSources = [
    "OpenAlex",
    semanticEnabled ? "Semantic Scholar" : "",
    arxivEnabled ? "arXiv" : ""
  ].filter(Boolean).join(" + ");

  return (
    <div className="status-strip" aria-label="系统状态">
      <div className="status-cell">
        <Server size={16} />
        <span className="status-copy">
          <strong>{config?.qwen_model || "qwen-plus"}</strong>
          <small>{config?.llm_enabled ? "百炼已连接" : "备用模式"}</small>
        </span>
      </div>
      <div className="status-cell">
        <Database size={16} />
        <span className="status-copy">
          <strong>{literatureSources}</strong>
          <small>{config?.materials_project_configured ? "Materials Project" : "本地数据"}</small>
        </span>
      </div>
      <div className="status-cell">
        <Activity size={16} />
        <span className="status-copy">
          <strong>{run ? `${statusLabel(run.status, run.control_action)} / ${stageLabel(run.current_stage)}` : "空闲"}</strong>
          {run && <small>引用{run.citation_frozen ? "已确认" : "待确认"} · 证据{run.evidence_frozen ? "已确认" : "待确认"}</small>}
        </span>
      </div>
    </div>
  );
}

function statusLabel(status: string, controlAction?: string) {
  if (status === "running" && controlAction === "pause") return "正在暂停";
  if (status === "running") return "运行中";
  if (status === "created") return "已创建";
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "paused") return "暂停待审";
  if (status === "abandoned") return "已废除";
  return status;
}

function stageLabel(stage: string) {
  const labels: Record<string, string> = {
    intent_router: "意图识别",
    planner: "任务规划",
    literature_search: "文献检索",
    citation_verification: "引用核验",
    evidence_ledger: "证据入账",
    literature_mining: "文献挖掘",
    paper_classification: "论文分类",
    scientific_data_profile: "数据画像",
    arena: "假设竞技",
    novelty_check: "新颖性检查",
    extract_code_urls: "代码链接提取",
    baseline_discover: "Baseline 发现",
    baseline_verify: "Baseline 验证",
    baseline_quality_gate: "Baseline 质量门",
    re_search_literature: "补充检索",
    experiment_design: "实验设计",
    code_experiment: "写代码并运行",
    macro_react: "宏观修复判断",
    report_writer: "报告生成",
    completed: "完成",
  };
  return labels[stage] || stage || "等待启动";
}
