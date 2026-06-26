import { Play, RefreshCw } from "lucide-react";

export function ResearchConsole({
  question,
  domain,
  maxPapers,
  workflowMode,
  enableSemanticScholar,
  enableArxiv,
  semanticScholarConfigured,
  busy,
  error,
  onQuestionChange,
  onDomainChange,
  onMaxPapersChange,
  onWorkflowModeChange,
  onEnableSemanticScholarChange,
  onEnableArxivChange,
  onStart,
  onRefresh,
  canRefresh
}: {
  question: string;
  domain: string;
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
  onMaxPapersChange: (value: number) => void;
  onWorkflowModeChange: (value: "auto" | "guided") => void;
  onEnableSemanticScholarChange: (value: boolean) => void;
  onEnableArxivChange: (value: boolean) => void;
  onStart: () => void;
  onRefresh: () => void;
}) {
  return (
    <div className="form">
      <div className="field">
        <label className="label">领域 / Domain</label>
        <select className="select" value={domain} onChange={(event) => onDomainChange(event.target.value)}>
          <option value="energy_materials">能源材料 / Energy materials</option>
          <option value="biomedicine">生物医学 / Biomedicine</option>
          <option value="climate_remote_sensing">气候与遥感 / Climate & remote sensing</option>
          <option value="custom">自定义 / Custom</option>
        </select>
      </div>
      <div className="field">
        <label className="label">科研问题 / Research question</label>
        <textarea className="textarea" value={question} onChange={(event) => onQuestionChange(event.target.value)} />
      </div>
      <div className="field">
        <label className="label">最大论文数 / Max papers</label>
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
        <label className="label">运行模式 / Workflow mode</label>
        <div className="segmented mode-toggle">
          <button
            type="button"
            className={workflowMode === "auto" ? "active" : ""}
            onClick={() => onWorkflowModeChange("auto")}
          >
            自动流程 / Auto
          </button>
          <button
            type="button"
            className={workflowMode === "guided" ? "active" : ""}
            onClick={() => onWorkflowModeChange("guided")}
          >
            人在回路 / Guided
          </button>
        </div>
        <small className="muted">
          Auto 一键跑完；Guided 会在 citation 和 evidence 审核后暂停。Auto runs end-to-end; Guided pauses for review gates.
        </small>
      </div>
      <label className="toggle-row">
        <input
          type="checkbox"
          checked={enableSemanticScholar}
          onChange={(event) => onEnableSemanticScholarChange(event.target.checked)}
        />
        <span>
          <strong>Semantic Scholar</strong>
          <small>{semanticScholarConfigured ? "使用 API Key / API enabled" : "可选补充检索源 / Optional source"}</small>
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
          <small>预印本补充检索源 / Preprint source</small>
        </span>
      </label>
      <button className="primary" onClick={onStart} disabled={busy}>
        {busy ? <RefreshCw size={17} /> : <Play size={17} />}
        启动工作流 / Start
      </button>
      {canRefresh && (
        <button className="secondary" onClick={onRefresh}>
          <RefreshCw size={16} />
          刷新状态 / Refresh
        </button>
      )}
      {error && <span className="badge warn">{error}</span>}
    </div>
  );
}
