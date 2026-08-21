import { BaselineIntakeRequest, BaselineStrategy, ManualBaselineInput } from "../../lib/api";

type Props = {
  value: BaselineIntakeRequest;
  onChange: (value: BaselineIntakeRequest) => void;
};

const emptyManual: ManualBaselineInput = {
  name: "",
  description: "",
  code_text: "",
  repository_url: "",
  run_command: "",
  dataset_description: "",
  metrics: [{ name: "accuracy", value: 0, split: "test" }],
  notes: ""
};

export function BaselineIntakePanel({ value, onChange }: Props) {
  const manual = value.manual || emptyManual;

  function setStrategy(strategy: BaselineStrategy) {
    if (strategy === "manual_upload") {
      onChange({ strategy, manual });
    } else {
      onChange({ strategy });
    }
  }

  function updateManual<K extends keyof typeof emptyManual>(key: K, next: (typeof emptyManual)[K]) {
    onChange({ strategy: "manual_upload", manual: { ...manual, [key]: next } });
  }

  function updateMetric(index: number, key: "name" | "value" | "split", next: string | number) {
    const metrics = [...(manual.metrics || [])];
    metrics[index] = { ...metrics[index], [key]: key === "value" ? Number(next) : String(next) };
    updateManual("metrics", metrics);
  }

  return (
    <section className="panel span-12 baseline-intake-panel">
      <div className="panel-heading">
        <h2>Baseline 来源</h2>
        <span className="badge">{strategyLabel(value.strategy)}</span>
      </div>
      <div className="actions">
        <button type="button" className={value.strategy === "manual_upload" ? "active" : ""} onClick={() => setStrategy("manual_upload")}>人工上传</button>
        <button type="button" className={value.strategy === "ai_generated" ? "active" : ""} onClick={() => setStrategy("ai_generated")}>AI 生成 demo</button>
        <button type="button" className={value.strategy === "none" ? "active" : ""} onClick={() => setStrategy("none")}>暂不提供</button>
      </div>
      {value.strategy === "manual_upload" && (
        <div className="form-grid">
          <label>名称<input value={manual.name} onChange={(e) => updateManual("name", e.target.value)} /></label>
          <label>仓库链接<input value={manual.repository_url || ""} onChange={(e) => updateManual("repository_url", e.target.value)} /></label>
          <label>运行命令<input value={manual.run_command || ""} onChange={(e) => updateManual("run_command", e.target.value)} /></label>
          <label>数据集说明<textarea value={manual.dataset_description} onChange={(e) => updateManual("dataset_description", e.target.value)} /></label>
          <label>方法说明<textarea value={manual.description} onChange={(e) => updateManual("description", e.target.value)} /></label>
          <label>代码文本<textarea value={manual.code_text || ""} onChange={(e) => updateManual("code_text", e.target.value)} /></label>
          <label>备注<textarea value={manual.notes} onChange={(e) => updateManual("notes", e.target.value)} /></label>
          <div className="metric-row">
            {(manual.metrics || []).map((metric, index) => (
              <span className="metric-editor" key={index}>
                <input value={metric.name} onChange={(e) => updateMetric(index, "name", e.target.value)} />
                <input type="number" value={metric.value} onChange={(e) => updateMetric(index, "value", e.target.value)} />
                <input value={metric.split || ""} onChange={(e) => updateMetric(index, "split", e.target.value)} />
              </span>
            ))}
          </div>
        </div>
      )}
      {value.strategy === "ai_generated" && <p className="muted">系统将创建一个简单可复现的 demo baseline；它不是外部验证的 SOTA baseline。</p>}
      {value.strategy === "none" && <p className="muted">报告会把 baseline 对比标记为不可用或降级，不生成强对比结论。</p>}
    </section>
  );
}

function strategyLabel(strategy: BaselineStrategy) {
  if (strategy === "manual_upload") return "人工上传";
  if (strategy === "ai_generated") return "AI 生成";
  return "无 baseline";
}
