import { Activity, ChevronDown, Play, RefreshCw, SlidersHorizontal } from "lucide-react";

export type WorkbenchVersion = "classic" | "seismic";
export type ResearchMode = "discovery" | "idea_refinement" | "experiment_assistance";

export function ResearchConsole({
  activeVersion,
  question,
  domain,
  researchMode,
  maxPapers,
  workflowMode,
  enableSemanticScholar,
  enableArxiv,
  semanticScholarConfigured,
  busy,
  error,
  canRefresh,
  onQuestionChange,
  onDomainChange,
  onResearchModeChange,
  onMaxPapersChange,
  onWorkflowModeChange,
  onEnableSemanticScholarChange,
  onEnableArxivChange,
  onStart,
  onRefresh
}: {
  activeVersion: WorkbenchVersion;
  question: string;
  domain: string;
  researchMode: ResearchMode;
  maxPapers: number;
  workflowMode: "auto" | "guided";
  enableSemanticScholar: boolean;
  enableArxiv: boolean;
  semanticScholarConfigured: boolean;
  busy: boolean;
  error: string;
  canRefresh: boolean;
  onQuestionChange: (value: string) => void;
  onDomainChange: (value: string) => void;
  onResearchModeChange: (value: ResearchMode) => void;
  onMaxPapersChange: (value: number) => void;
  onWorkflowModeChange: (value: "auto" | "guided") => void;
  onEnableSemanticScholarChange: (value: boolean) => void;
  onEnableArxivChange: (value: boolean) => void;
  onStart: () => void;
  onRefresh: () => void;
}) {
  const isSeismic = activeVersion === "seismic";

  return (
    <div className="form">
      {isSeismic && (
        <div className="field">
          <label className="label">科研模式</label>
          <div className="segmented mode-toggle">
            <button
              type="button"
              className={researchMode === "discovery" ? "active" : ""}
              onClick={() => onResearchModeChange("discovery")}
            >
              自动发现
            </button>
            <button
              type="button"
              className={researchMode === "idea_refinement" ? "active" : ""}
              onClick={() => onResearchModeChange("idea_refinement")}
            >
              创意精修
            </button>
            <button
              type="button"
              className={researchMode === "experiment_assistance" ? "active" : ""}
              onClick={() => onResearchModeChange("experiment_assistance")}
            >
              实验辅助
            </button>
          </div>
        </div>
      )}

      {!isSeismic && (
        <div className="field">
          <label className="label">研究领域</label>
          <select className="select" value={domain} onChange={(event) => onDomainChange(event.target.value)}>
            <option value="energy_materials">能源材料</option>
            <option value="biomedicine">生物医学</option>
            <option value="climate_remote_sensing">气候与遥感</option>
            <option value="custom">自定义</option>
          </select>
        </div>
      )}

      <div className="field">
        <label className="label">科研问题</label>
        <textarea className="textarea" value={question} onChange={(event) => onQuestionChange(event.target.value)} />
      </div>

      <details className="research-settings">
        <summary>
          <span><SlidersHorizontal size={15} /> 研究设置</span>
          <span className="settings-summary-value">{maxPapers} 篇 · {workflowMode === "auto" ? "自动" : "引导"}</span>
          <ChevronDown className="settings-chevron" size={15} />
        </summary>
        <div className="research-settings-body">
          <div className="field">
            <label className="label">最大论文数</label>
            <input
              className="input"
              min={3}
              max={12}
              type="number"
              value={maxPapers}
              onChange={(event) => onMaxPapersChange(Number(event.target.value))}
            />
          </div>

          <div className="field">
            <label className="label">运行模式</label>
            <div className="segmented workflow-mode-toggle">
              <button
                type="button"
                className={workflowMode === "auto" ? "active" : ""}
                onClick={() => onWorkflowModeChange("auto")}
              >
                自动模式
              </button>
              <button
                type="button"
                className={workflowMode === "guided" ? "active" : ""}
                onClick={() => onWorkflowModeChange("guided")}
              >
                引导模式
              </button>
            </div>
          </div>

          <div className="research-source-grid">
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={enableSemanticScholar}
                onChange={(event) => onEnableSemanticScholarChange(event.target.checked)}
              />
              <span>
                <strong>Semantic Scholar</strong>
                <small>{semanticScholarConfigured ? "API 已启用" : "可选检索源"}</small>
              </span>
            </label>

            <label className="toggle-row">
              <input
                type="checkbox"
                checked={enableArxiv}
                onChange={(event) => onEnableArxivChange(event.target.checked)}
              />
              <span>
                <strong>arXiv</strong>
                <small>预印本检索源</small>
              </span>
            </label>
          </div>
        </div>
      </details>

      <div className="console-actions">
        <button className="primary" onClick={onStart} disabled={busy}>
          {busy ? <RefreshCw className="spin" size={17} /> : <Play size={17} />}
          启动研究
        </button>

        {canRefresh && (
          <button className="secondary" onClick={onRefresh} aria-label="刷新当前研究">
            <RefreshCw size={16} />
            刷新
          </button>
        )}
      </div>

      {isSeismic && (
        <span className="badge version-badge">
          <Activity size={13} />
          {researchModeLabel(researchMode)}
        </span>
      )}
      {error && <span className="badge warn">{error}</span>}
    </div>
  );
}

function researchModeLabel(mode: ResearchMode) {
  if (mode === "idea_refinement") return "创意精修";
  if (mode === "experiment_assistance") return "实验辅助";
  return "自动发现";
}
