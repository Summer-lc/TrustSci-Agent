import { ResearchRun } from "../../lib/api";

export function ExperimentPlanPanel({ run }: { run: ResearchRun | null }) {
  const plan = run?.experiment_plan;
  return (
    <section className="panel span-6">
      <h2>Experiment Plan</h2>
      {!plan && <p className="muted">暂无实验计划</p>}
      {plan && (
        <div className="dense">
          <div>
            <span className="label">Datasets</span>
            <p>{plan.datasets.join(" · ")}</p>
          </div>
          <div>
            <span className="label">Metrics</span>
            <p>{plan.metrics.join(" · ")}</p>
          </div>
          <div>
            <span className="label">Baselines</span>
            <p>{plan.baselines.join(" · ")}</p>
          </div>
          <div>
            <span className="label">Target</span>
            <p>{plan.target}</p>
          </div>
        </div>
      )}
    </section>
  );
}

