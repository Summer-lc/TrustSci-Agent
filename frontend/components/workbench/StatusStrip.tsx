import { Activity, Database, Server } from "lucide-react";
import { PublicConfig, ResearchRun } from "../../lib/api";

export function StatusStrip({ config, run }: { config: PublicConfig | null; run: ResearchRun | null }) {
  return (
    <div className="status-strip">
      <div className="status-cell">
        <Server size={16} />
        <span>{config?.qwen_model || "qwen-plus"}</span>
        <span className={`badge ${config?.llm_enabled ? "good" : "warn"}`}>
          {config?.llm_enabled ? "Bailian" : "fallback"}
        </span>
      </div>
      <div className="status-cell">
        <Database size={16} />
        <span>{config?.semantic_scholar_configured ? "OpenAlex + S2 + arXiv" : "OpenAlex + arXiv"}</span>
        <span className="badge">{config?.materials_project_configured ? "MP" : "local data"}</span>
      </div>
      <div className="status-cell">
        <Activity size={16} />
        <span>{run ? `${run.status} / ${run.current_stage}` : "idle"}</span>
      </div>
    </div>
  );
}
