import type { CodeExperimentResult } from "../../lib/api";

const OUTCOME_BADGE: Record<string, string> = {
  completed_positive: "good",
  completed_negative: "warn",
  failed: "warn",
};

export function ExperimentResultsPanel({ ce }: { ce: CodeExperimentResult }) {
  const { comparison, acceptance_gate, summary } = ce;
  const baselineMetrics = comparison.baseline_metrics;
  const methodMetrics = comparison.method_metrics;
  const baselinePerClass = metricMap(baselineMetrics.per_class_f1);
  const methodPerClass = metricMap(methodMetrics.per_class_f1);
  const classLabels = Array.from(new Set([...Object.keys(baselinePerClass), ...Object.keys(methodPerClass)])).sort();
  return (
    <section className="panel span-12 code-panel">
      <h3>实验结果</h3>
      <div className="badges">
        <span className={`badge ${OUTCOME_BADGE[comparison.outcome] ?? "warn"}`}>
          {outcomeLabel(comparison.outcome)}
        </span>
        {summary.best_metric != null && (
          <span className="badge">最佳指标 {summary.best_metric.toFixed(3)}</span>
        )}
      </div>
      <div className="metrics-table-wrap">
        <table className="metrics-table">
          <thead><tr><th>指标</th><th>Baseline</th><th>方法</th></tr></thead>
          <tbody>
            <tr><td>准确率</td><td>{formatMetric(baselineMetrics.accuracy)}</td><td>{formatMetric(methodMetrics.accuracy)}</td></tr>
            <tr><td>宏平均 F1</td><td>{formatMetric(baselineMetrics.macro_f1)}</td><td>{formatMetric(methodMetrics.macro_f1)}</td></tr>
            {classLabels.map((label) => (
              <tr key={label}>
                <td>F1：{label}</td>
                <td>{formatMetric(baselinePerClass[label])}</td>
                <td>{formatMetric(methodPerClass[label])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="code-kv">
        <span><strong>测试通过</strong>{acceptance_gate.tests_pass ? "是" : "否"}</span>
        <span><strong>指标已生成</strong>{acceptance_gate.metrics_generated ? "是" : "否"}</span>
        <span><strong>对比已写出</strong>{acceptance_gate.baseline_comparison_written ? "是" : "否"}</span>
      </div>
      {comparison.notes.length > 0 && (
        <ul className="notes">{comparison.notes.map((note, index) => <li key={index}>{note}</li>)}</ul>
      )}
    </section>
  );
}

function outcomeLabel(outcome: string) {
  if (outcome === "completed_positive") return "完成：方法优于 baseline";
  if (outcome === "completed_negative") return "完成：方法未优于 baseline";
  if (outcome === "failed") return "失败";
  return outcome;
}

function formatMetric(value: number | Record<string, number> | undefined) {
  return typeof value === "number" ? value.toFixed(3) : "-";
}

function metricMap(value: number | Record<string, number> | undefined) {
  return typeof value === "object" && value !== null ? value : {};
}
