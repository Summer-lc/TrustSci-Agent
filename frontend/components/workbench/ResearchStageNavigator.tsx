import { CheckCircle2, Circle, LoaderCircle, TriangleAlert } from "lucide-react";

import { ResearchRun } from "../../lib/api";
import { groupRunStages, WorkbenchStageId } from "../../lib/workbench";


export function ResearchStageNavigator({
  run,
  activeStage,
  onSelect,
}: {
  run: ResearchRun | null;
  activeStage: WorkbenchStageId;
  onSelect: (stage: WorkbenchStageId) => void;
}) {
  const groups = groupRunStages(run?.steps || []);
  return (
    <nav className="stage-navigator" aria-label="研究流程阶段">
      {groups.map((group, index) => {
        const status = aggregateStatus(group.steps);
        const completed = group.steps.filter((step) => ["completed", "skipped"].includes(step.status)).length;
        return (
          <button
            className={`stage-card ${activeStage === group.id ? "active" : ""} ${status}`}
            key={group.id}
            onClick={() => onSelect(group.id)}
            type="button"
            aria-current={activeStage === group.id ? "step" : undefined}
            title={group.description}
          >
            <span className="stage-index">{index + 1}</span>
            <span className="stage-copy">
              <strong>{group.label}</strong>
              {activeStage === group.id && <small>{group.description}</small>}
              {activeStage === group.id && group.steps.length > 0 && <em>{completed}/{group.steps.length} 个步骤完成</em>}
              {group.id === "experiment" && (run?.experiment_redesign_round || 0) > 0 && (
                <em className="loop-label">实验重设计第 {run?.experiment_redesign_round} 轮</em>
              )}
            </span>
            <span className="stage-status" aria-label={status}>
              {status === "completed" ? <CheckCircle2 size={17} /> : status === "running" ? <LoaderCircle size={17} /> : status === "attention" ? <TriangleAlert size={17} /> : <Circle size={17} />}
            </span>
          </button>
        );
      })}
    </nav>
  );
}

function aggregateStatus(steps: ResearchRun["steps"]): "pending" | "running" | "attention" | "completed" {
  if (steps.some((step) => ["waiting_action", "failed"].includes(step.status))) return "attention";
  if (steps.some((step) => ["running", "retrying"].includes(step.status))) return "running";
  if (steps.length > 0 && steps.every((step) => ["completed", "skipped"].includes(step.status))) return "completed";
  return "pending";
}
