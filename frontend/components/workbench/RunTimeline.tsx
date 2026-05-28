import { ResearchRun } from "../../lib/api";

export function RunTimeline({ run }: { run: ResearchRun | null }) {
  return (
    <section className="panel span-4">
      <h2>Run Timeline</h2>
      <div className="progress"><div style={{ width: `${Math.round((run?.progress || 0) * 100)}%` }} /></div>
      <div className="timeline" style={{ marginTop: 14 }}>
        {(run?.steps || []).map((step) => (
          <div className="step" key={step.name}>
            <span className={`dot ${step.status}`} />
            <span>{step.name}</span>
            <span className="badge">{step.status}</span>
            {step.summary && <span className="muted" style={{ gridColumn: "2 / 4" }}>{step.summary}</span>}
          </div>
        ))}
        {!run?.steps.length && <p className="muted">等待任务启动</p>}
      </div>
    </section>
  );
}

