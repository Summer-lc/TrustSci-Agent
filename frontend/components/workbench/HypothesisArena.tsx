import { CheckCircle2, FlaskConical, MessageSquareText } from "lucide-react";
import { ResearchRun } from "../../lib/api";

type Props = {
  run: ResearchRun | null;
  busy?: boolean;
  onSelect: (hypothesisId: string) => void;
};

export function HypothesisArena({ run, busy = false, onSelect }: Props) {
  return (
    <section className="panel span-6">
      <div className="panel-heading">
        <h2><FlaskConical size={16} /> 假设评审</h2>
        <span className="badge">{run?.hypotheses.length || 0} 个候选</span>
      </div>
      <div className="list">
        {(run?.hypotheses || []).map((hypothesis) => (
          <article className="item" key={hypothesis.hypothesis_id}>
            <div className="item-title">{hypothesis.hypothesis_id}: {hypothesis.statement}</div>
            {hypothesis.revised_statement && (
              <p className="muted">修订后：{hypothesis.revised_statement}</p>
            )}
            {hypothesis.critic && (
              <p className="muted">
                新颖性 {hypothesis.critic.novelty}/10 · 可验证性 {hypothesis.critic.verifiability}/10 ·
                证据支持 {hypothesis.critic.evidence_support}/10 · 任务适配 {hypothesis.critic.competition_fit}/10
              </p>
            )}
            <div className="item-meta">{hypothesis.critic?.risk}</div>
            {hypothesis.selection_rationale && (
              <div className="item-meta"><CheckCircle2 size={13} /> {hypothesis.selection_rationale}</div>
            )}
            <div className="dense compact">
              {hypothesis.reviewer_comments.slice(0, 3).map((comment) => (
                <p key={`${hypothesis.hypothesis_id}-${comment.reviewer}`}>
                  <MessageSquareText size={13} /> <strong>{comment.reviewer}</strong>（{comment.score}/10）：{comment.required_action}
                </p>
              ))}
            </div>
            {hypothesis.revision_history[0] && (
              <div className="item-meta">修订依据：{hypothesis.revision_history[0].rationale}</div>
            )}
            <div className="item-actions">
              <span className={`badge ${hypothesis.selected ? "good" : ""}`}>
                {hypothesis.selected ? "已选中" : "候选"}
              </span>
              <button
                className="secondary"
                onClick={() => onSelect(hypothesis.hypothesis_id)}
                disabled={busy || hypothesis.selected}
              >
                <CheckCircle2 size={14} /> 选择
              </button>
            </div>
          </article>
        ))}
        {!run?.hypotheses.length && <p className="muted">暂无候选假设。</p>}
      </div>
    </section>
  );
}
