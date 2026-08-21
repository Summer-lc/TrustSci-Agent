import { useState } from "react";
import type { CodeExperimentResult } from "../../lib/api";

export function CodePlanPanel({ ce }: { ce: CodeExperimentResult }) {
  const [open, setOpen] = useState(false);
  const fcp = ce.fair_comparison_plan;
  return (
    <section className="panel span-6 code-panel">
      <h3>代码实验计划</h3>
      <div className="code-kv">
        <span><strong>测试框架</strong>{ce.harness_version}</span>
        <span><strong>模型类型</strong>{ce.model_family}</span>
        <span><strong>Baseline 来源</strong>{ce.baseline_source}</span>
      </div>
      <div className="code-kv">
        <span><strong>数据划分</strong>{fcp.split_strategy}</span>
        <span><strong>评估指标</strong>{fcp.metrics.join(", ")}</span>
      </div>
      <p className="muted">{fcp.preprocessing}</p>
      <button className="secondary" onClick={() => setOpen((value) => !value)}>
        {open ? "隐藏 model.py" : "查看 model.py"}
      </button>
      {open && (
        <pre className="code-scroll" style={{ maxHeight: 360, overflow: "auto" }}>
{ce.model_py_source}
        </pre>
      )}
    </section>
  );
}
