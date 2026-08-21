import { ResearchRun } from "../../lib/api";

export function ResultAnalysisPanel({ run }: { run: ResearchRun | null }) {
  if (!run?.result_evaluation && !run?.ablation_analysis && !run?.result_interpretation) return null;
  return <section className="panel span-12"><div className="panel-header"><h2>结果支持判断</h2><span className="badge">{run.result_evaluation?.verdict || "pending"}</span></div>
    <p>{run.result_evaluation?.reasoning}</p>
    {run.result_evaluation?.supported_claims.map((x,i)=><p key={`s${i}`}>✓ {x}</p>)}
    {run.result_evaluation?.unsupported_claims.map((x,i)=><p key={`u${i}`}>⚠ {x}</p>)}
    <h3>消融分析</h3><p>{run.ablation_analysis?.summary || "尚无消融证据"}</p>
    <h3>证据边界</h3><p>{run.result_interpretation?.evidence_boundary}</p>
    {run.result_interpretation?.next_experiments.map((x,i)=><p key={`n${i}`}>→ {x}</p>)}
  </section>;
}
