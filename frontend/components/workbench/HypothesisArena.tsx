import { FlaskConical } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function HypothesisArena({ run }: { run: ResearchRun | null }) {
  return (
    <section className="panel span-6">
      <h2><FlaskConical size={16} /> Hypothesis Arena</h2>
      <div className="list">
        {(run?.hypotheses || []).map((hypothesis) => (
          <article className="item" key={hypothesis.hypothesis_id}>
            <div className="item-title">{hypothesis.hypothesis_id}: {hypothesis.statement}</div>
            {hypothesis.critic && (
              <p className="muted">
                novelty {hypothesis.critic.novelty}/10 · verifiability {hypothesis.critic.verifiability}/10 · {hypothesis.critic.risk}
              </p>
            )}
            <span className={`badge ${hypothesis.selected ? "good" : ""}`}>
              {hypothesis.selected ? "selected" : "candidate"}
            </span>
          </article>
        ))}
        {!run?.hypotheses.length && <p className="muted">暂无候选假设</p>}
      </div>
    </section>
  );
}

