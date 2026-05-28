import { Clock3 } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function RunHistory({
  runs,
  selectedRunId,
  onSelect
}: {
  runs: ResearchRun[];
  selectedRunId?: string;
  onSelect: (run: ResearchRun) => void;
}) {
  return (
    <section className="sidebar-section">
      <div className="section-title">
        <Clock3 size={15} />
        <span>Runs</span>
      </div>
      <div className="run-list">
        {runs.slice(0, 8).map((run) => (
          <button
            className={`run-row ${run.run_id === selectedRunId ? "active" : ""}`}
            key={run.run_id}
            onClick={() => onSelect(run)}
          >
            <span>{run.run_id}</span>
            <span>{run.status}</span>
          </button>
        ))}
        {!runs.length && <span className="muted compact">暂无运行记录</span>}
      </div>
    </section>
  );
}

