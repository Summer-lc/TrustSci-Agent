import { useState } from "react";
import type { CodeExperimentResult } from "../../lib/api";

export function CodeDebugPanel({ ce }: { ce: CodeExperimentResult }) {
  const [selectedRound, setSelectedRound] = useState<number>(ce.debug_log[0]?.round ?? 0);
  const entry = ce.debug_log.find((item) => item.round === selectedRound);
  return (
    <section className="panel span-6 code-panel">
      <h3>代码调试记录</h3>
      <ol className="timeline">
        {ce.iteration_log.map((item) => (
          <li
            key={item.round}
            className={item.tests_passed ? "ok" : "err"}
            onClick={() => setSelectedRound(item.round)}
            style={{ cursor: "pointer" }}
          >
            <strong>第 {item.round} 轮</strong> {phaseLabel(item.phase)} · {item.tests_passed ? "测试通过" : "测试失败"}
            <code> {item.model_py_hash}</code>
          </li>
        ))}
      </ol>
      {entry?.traceback_full && (
        <pre className="code-scroll" style={{ maxHeight: 320, overflow: "auto" }}>
{entry.traceback_full}
        </pre>
      )}
    </section>
  );
}

function phaseLabel(phase: string) {
  if (phase === "initial") return "初始生成";
  if (phase === "repair") return "错误修复";
  if (phase === "macro") return "Top1 方案重写";
  return phase;
}
