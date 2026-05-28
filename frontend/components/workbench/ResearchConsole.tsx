import { Play, RefreshCw } from "lucide-react";

export function ResearchConsole({
  question,
  domain,
  maxPapers,
  busy,
  error,
  onQuestionChange,
  onDomainChange,
  onMaxPapersChange,
  onStart,
  onRefresh,
  canRefresh
}: {
  question: string;
  domain: string;
  maxPapers: number;
  busy: boolean;
  error: string;
  canRefresh: boolean;
  onQuestionChange: (value: string) => void;
  onDomainChange: (value: string) => void;
  onMaxPapersChange: (value: number) => void;
  onStart: () => void;
  onRefresh: () => void;
}) {
  return (
    <div className="form">
      <div className="field">
        <label className="label">领域</label>
        <select className="select" value={domain} onChange={(event) => onDomainChange(event.target.value)}>
          <option value="energy_materials">能源材料</option>
          <option value="biomedicine">生物医学</option>
          <option value="climate_remote_sensing">气候与遥感</option>
          <option value="custom">自定义</option>
        </select>
      </div>
      <div className="field">
        <label className="label">科研问题</label>
        <textarea className="textarea" value={question} onChange={(event) => onQuestionChange(event.target.value)} />
      </div>
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
      <button className="primary" onClick={onStart} disabled={busy}>
        {busy ? <RefreshCw size={17} /> : <Play size={17} />}
        启动工作流
      </button>
      {canRefresh && (
        <button className="secondary" onClick={onRefresh}>
          <RefreshCw size={16} />
          刷新状态
        </button>
      )}
      {error && <span className="badge warn">{error}</span>}
    </div>
  );
}

