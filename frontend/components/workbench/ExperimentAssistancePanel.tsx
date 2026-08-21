import { ExperimentAssistanceInput } from "../../lib/api";

export function ExperimentAssistancePanel({ value, onChange }: { value: ExperimentAssistanceInput; onChange: (value: ExperimentAssistanceInput) => void }) {
  const setMetric = (kind: "baseline_metrics" | "method_metrics", key: "name" | "value", raw: string) => {
    const current = value[kind][0] || { name: "accuracy", value: 0 };
    onChange({ ...value, [kind]: [{ ...current, [key]: key === "value" ? Number(raw) : raw }] });
  };
  return <section className="panel span-12">
    <div className="panel-header"><h2>实验辅助输入</h2><span className="badge">不执行所提交代码</span></div>
    <label>实验目标<textarea value={value.objective} onChange={e => onChange({...value, objective:e.target.value})}/></label>
    <label>方法说明<textarea value={value.method_summary} onChange={e => onChange({...value, method_summary:e.target.value})}/></label>
    <div className="form-grid">
      <label>Baseline 指标名<input value={value.baseline_metrics[0]?.name || "accuracy"} onChange={e=>setMetric("baseline_metrics","name",e.target.value)}/></label>
      <label>Baseline 值<input type="number" step="any" value={value.baseline_metrics[0]?.value ?? 0} onChange={e=>setMetric("baseline_metrics","value",e.target.value)}/></label>
      <label>方法指标名<input value={value.method_metrics[0]?.name || "accuracy"} onChange={e=>setMetric("method_metrics","name",e.target.value)}/></label>
      <label>方法值<input type="number" step="any" value={value.method_metrics[0]?.value ?? 0} onChange={e=>setMetric("method_metrics","value",e.target.value)}/></label>
    </div>
    <label>已有代码（只保存与审阅）<textarea value={value.source_code || ""} onChange={e=>onChange({...value,source_code:e.target.value})}/></label>
  </section>;
}
