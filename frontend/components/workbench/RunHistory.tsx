import { Ban, Clock3, Eye, Pause, Play, RotateCcw } from "lucide-react";
import { ResearchRun, RestorableWorkspace } from "../../lib/api";
import { runDisplayName, runHistoryActions, stepLabel } from "../../lib/workbench";

export function RunHistory({
  runs,
  workspaces,
  selectedRunId,
  restoring,
  controllingRunId,
  onSelect,
  onRestore,
  onRecover,
  onPause,
  onResume,
  onAbandon,
}: {
  runs: ResearchRun[];
  workspaces: RestorableWorkspace[];
  selectedRunId?: string;
  restoring: boolean;
  controllingRunId?: string | null;
  onSelect: (run: ResearchRun) => void;
  onRestore: (runId: string, resumeAfterRestore?: boolean) => void;
  onRecover: (runId: string) => void;
  onPause: (runId: string) => void;
  onResume: (runId: string) => void;
  onAbandon: (runId: string) => void;
}) {
  const runIds = new Set(runs.map((run) => run.run_id));
  const restorable = workspaces.filter((workspace) => !runIds.has(workspace.run_id)).slice(0, 5);

  return (
    <section className="sidebar-section">
      <div className="section-title">
        <Clock3 size={15} />
        <span>历史任务</span>
      </div>
      <div className="run-list">
        {runs.slice(0, 8).map((run) => {
          const actions = runHistoryActions(run);
          const busy = restoring || controllingRunId === run.run_id;
          return (
          <div className={`run-history-item ${run.run_id === selectedRunId ? "active" : ""}`} key={run.run_id}>
            <button className="run-row" onClick={() => onSelect(run)} type="button">
              <span>
                <strong title={run.question}>{runDisplayName(run)}</strong>
                <small>{stageLabel(run.current_stage)}{run.updated_at ? ` · ${formatUpdatedAt(run.updated_at)}` : ""}</small>
              </span>
              <span>{statusLabel(run.status, run.control_action)}</span>
            </button>
            {actions.length > 0 && (
              <div className="run-history-actions">
                {actions.includes("pause") && <button disabled={busy} onClick={() => onPause(run.run_id)} type="button"><Pause size={13} /> 暂停</button>}
                {actions.includes("resume") && <button className="resume" disabled={busy} onClick={() => onResume(run.run_id)} type="button"><Play size={13} /> 继续运行</button>}
                {actions.includes("review") && <button className="resume" disabled={busy} onClick={() => onSelect(run)} type="button"><Eye size={13} /> 查看并处理</button>}
                {actions.includes("recover") && <button disabled={busy} onClick={() => onRecover(run.run_id)} type="button"><RotateCcw size={13} /> 恢复</button>}
                {actions.includes("abandon") && <button className="danger" disabled={busy} onClick={() => onAbandon(run.run_id)} type="button"><Ban size={13} /> 废除</button>}
              </div>
            )}
          </div>
          );
        })}
        {!runs.length && <span className="muted compact">暂无运行记录</span>}
      </div>
      {restorable.length > 0 && (
        <>
          <div className="section-title">
            <RotateCcw size={15} />
            <span>已保存工作区</span>
          </div>
          <div className="run-list">
            {restorable.map((workspace) => (
              <div className="run-history-item workspace-history-item" key={workspace.run_id}>
                <div className="run-row static-row">
                  <span>
                    <strong title={workspace.question}>{runDisplayName(workspace)}</strong>
                    <small>{stageLabel(workspace.current_stage)}{workspace.updated_at ? ` · ${formatUpdatedAt(workspace.updated_at)}` : ""}</small>
                  </span>
                  <span>{statusLabel(workspace.status)}</span>
                </div>
                <div className="run-history-actions">
                  <button
                    className="resume"
                    disabled={restoring}
                    onClick={() => onRestore(workspace.run_id, workspace.status === "paused" && workspace.pause_reason === "user")}
                    type="button"
                  >
                    {workspace.status === "paused" && workspace.pause_reason === "user" ? <><Play size={13} /> 恢复并继续</> : <><Eye size={13} /> 恢复查看</>}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function statusLabel(status: string, controlAction?: string | null) {
  if (status === "running" && controlAction === "pause") return "正在暂停";
  if (status === "running") return "运行中";
  if (status === "created") return "已创建";
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "paused") return "暂停";
  if (status === "abandoned") return "已废除";
  return status;
}

function stageLabel(stage: string) {
  if (stage === "created" || stage === "queued") return "等待启动";
  if (stage === "completed") return "全部完成";
  if (stage === "failed") return "执行失败";
  if (stage === "awaiting_citation_review") return "等待引用审查";
  if (stage === "awaiting_evidence_review") return "等待证据审查";
  return stepLabel(stage || "created");
}

function formatUpdatedAt(value: string) {
  return value.slice(0, 16).replace("T", " ");
}
