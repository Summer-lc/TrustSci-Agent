import { ResearchRun } from "../../lib/api";

const stepLabels: Record<string, string> = {
  planner: "任务规划 / Planning",
  literature_search: "文献检索 / Literature",
  citation_verification: "引用核验 / Citation",
  evidence_ledger: "证据入账 / Evidence",
  literature_mining: "文献挖掘 / Mining",
  scientific_data_profile: "数据画像 / Data",
  hypothesis_debate: "假设评审 / Hypotheses",
  experiment_design: "实验设计 / Experiment",
  report_writer: "报告生成 / Report",
  claim_verification: "结论核验 / Claims"
};

export function RunTimeline({ run, compact = false }: { run: ResearchRun | null; compact?: boolean }) {
  const activeStep = run?.steps.find((step) => step.status === "running");
  const progress = Math.round((run?.progress || 0) * 100);

  if (compact) {
    return (
      <section className="sidebar-section workflow-summary">
        <div className="section-title">
          <span>运行进度 / Workflow</span>
          <span className="badge">{run ? `${progress}%` : "idle"}</span>
        </div>
        <div className="progress"><div style={{ width: `${progress}%` }} /></div>
        <div className="mini-timeline">
          {(run?.steps || []).map((step) => (
            <div className="mini-step" key={step.name} title={step.summary || step.name}>
              <span className={`dot ${step.status}`} />
              <span>{stepLabels[step.name] || step.name}</span>
            </div>
          ))}
          {!run?.steps.length && <span className="muted compact">等待任务启动 / Waiting</span>}
        </div>
        {activeStep && (
          <p className="muted compact">当前 / Current: {stepLabels[activeStep.name] || activeStep.name}</p>
        )}
      </section>
    );
  }

  return (
    <section className="panel span-12">
      <h2>运行时间线 / Run Timeline</h2>
      <div className="progress"><div style={{ width: `${progress}%` }} /></div>
      {activeStep && (
        <div className="callout" style={{ marginTop: 14 }}>
          <strong>当前工作 / Current work: {stepLabels[activeStep.name] || activeStep.name}</strong>
          <p className="muted">{activeStep.summary || "正在运行 workflow step / Running workflow step."}</p>
        </div>
      )}
      <div className="timeline" style={{ marginTop: 14 }}>
        {(run?.steps || []).map((step) => (
          <div className="step" key={step.name}>
            <span className={`dot ${step.status}`} />
            <span>{stepLabels[step.name] || step.name}</span>
            <span className="badge">{step.status}</span>
            {step.summary && <span className="muted" style={{ gridColumn: "2 / 4" }}>{step.summary}</span>}
          </div>
        ))}
        {!run?.steps.length && <p className="muted">等待任务启动 / Waiting for workflow</p>}
      </div>
      {Boolean(run?.errors?.length) && (
        <div className="callout danger" style={{ marginTop: 14 }}>
          <strong>工作流错误 / Workflow errors</strong>
          {run?.errors.map((error, index) => <p className="muted" key={`${error}-${index}`}>{error}</p>)}
        </div>
      )}
    </section>
  );
}
