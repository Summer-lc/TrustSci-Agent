import { ResearchRun } from "../../lib/api";

export function ExperimentPlanPanel({ run }: { run: ResearchRun | null }) {
  const plan = run?.experiment_plan;
  return (
    <section className="panel span-6">
      <h2>实验计划 / Experiment Plan</h2>
      {!plan && <p className="muted">暂无实验计划 / No experiment plan yet.</p>}
      {plan && (
        <div className="dense">
          <div>
            <span className="label">数据集 / Datasets</span>
            <p>{plan.datasets.join(" · ")}</p>
          </div>
          <div>
            <span className="label">指标 / Metrics</span>
            <p>{plan.metrics.join(" · ")}</p>
          </div>
          <div>
            <span className="label">基线 / Baselines</span>
            <p>{plan.baselines.join(" · ")}</p>
          </div>
          <div>
            <span className="label">目标 / Target</span>
            <p>{plan.target}</p>
          </div>
        </div>
      )}
    </section>
  );
}
