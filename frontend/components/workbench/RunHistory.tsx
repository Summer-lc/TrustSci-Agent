import { Clock3, RotateCcw } from "lucide-react";
import { ResearchRun, RestorableWorkspace } from "../../lib/api";

export function RunHistory({
  runs,
  workspaces,
  selectedRunId,
  restoring,
  onSelect,
  onRestore
}: {
  runs: ResearchRun[];
  workspaces: RestorableWorkspace[];
  selectedRunId?: string;
  restoring: boolean;
  onSelect: (run: ResearchRun) => void;
  onRestore: (runId: string) => void;
}) {
  const runIds = new Set(runs.map((run) => run.run_id));
  const restorable = workspaces.filter((workspace) => !runIds.has(workspace.run_id)).slice(0, 5);

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
      {restorable.length > 0 && (
        <>
          <div className="section-title">
            <RotateCcw size={15} />
            <span>Recover</span>
          </div>
          <div className="run-list">
            {restorable.map((workspace) => (
              <button
                className="run-row"
                disabled={restoring}
                key={workspace.run_id}
                onClick={() => onRestore(workspace.run_id)}
              >
                <span>{workspace.run_id}</span>
                <span>{workspace.status}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
