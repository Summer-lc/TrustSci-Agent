import { ResearchRun } from "../../lib/api";

export function ExperimentPlanPanel({ run }: { run: ResearchRun | null }) {
  const plan = run?.experiment_plan;
  return (
    <section className="panel span-6">
      <h2>实验计划</h2>
      {!plan && <p className="muted">暂无实验计划。</p>}
      {plan && (
        <div className="dense">
          <div>
            <span className="label">数据集</span>
            <p>{plan.datasets.join(" · ")}</p>
          </div>
          <div>
            <span className="label">指标</span>
            <p>{plan.metrics.join(" · ")}</p>
          </div>
          <div>
            <span className="label">基线</span>
            <p>{plan.baselines.join(" · ")}</p>
          </div>
          <div>
            <span className="label">目标</span>
            <p>{plan.target}</p>
          </div>
        </div>
      )}
    </section>
  );
}
