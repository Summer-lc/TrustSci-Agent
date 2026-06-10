import { Activity, Database, Server } from "lucide-react";
import { PublicConfig, ResearchRun } from "../../lib/api";

export function StatusStrip({ config, run }: { config: PublicConfig | null; run: ResearchRun | null }) {
  const semanticEnabled = run?.constraints.enable_semantic_scholar || (!run && config?.semantic_scholar_configured);
  const arxivEnabled = run?.constraints.enable_arxiv ?? true;
  const literatureSources = [
    "OpenAlex",
    semanticEnabled ? "S2" : "",
    arxivEnabled ? "arXiv" : ""
  ].filter(Boolean).join(" + ");

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
        <span>{literatureSources}</span>
        <span className="badge">{config?.materials_project_configured ? "MP" : "local data"}</span>
      </div>
      <div className="status-cell">
        <Activity size={16} />
        <span>{run ? `${run.status} / ${run.current_stage}` : "idle"}</span>
        {run && (
          <>
            <span className={`badge ${run.citation_frozen ? "good" : "warn"}`}>
              citations {run.citation_frozen ? "frozen" : "open"}
            </span>
            <span className={`badge ${run.evidence_frozen ? "good" : "warn"}`}>
              evidence {run.evidence_frozen ? "frozen" : "open"}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
