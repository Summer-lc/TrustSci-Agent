import { Check, FileSearch, Lock, RotateCcw, X } from "lucide-react";
import { ResearchRun } from "../../lib/api";

type EvidenceDecision = "pending" | "accepted" | "rejected";

type Props = {
  run: ResearchRun | null;
  busy?: boolean;
  onDecision: (evidenceId: string, decision: EvidenceDecision) => void;
  onFreeze: () => void;
  onUnfreeze: () => void;
};

export function EvidenceBoard({ run, busy = false, onDecision, onFreeze, onUnfreeze }: Props) {
  const evidence = run?.evidence || [];
  const frozenCount = run?.frozen_evidence_ids.length || 0;

  return (
    <section className="panel span-8">
      <div className="panel-heading">
        <h2><FileSearch size={16} /> Evidence Board</h2>
        <div className="actions">
          <span className={`badge ${run?.evidence_frozen ? "good" : "warn"}`}>
            {run?.evidence_frozen ? `frozen ${frozenCount}` : "open gate"}
          </span>
          {run?.evidence_frozen ? (
            <button className="secondary" onClick={onUnfreeze} disabled={busy || !run}>
              <RotateCcw size={14} /> 解冻
            </button>
          ) : (
            <button className="secondary" onClick={onFreeze} disabled={busy || !run || evidence.length === 0}>
              <Lock size={14} /> 冻结
            </button>
          )}
        </div>
      </div>
      <div className="list">
        {evidence.slice(0, 8).map((item) => (
          <article className="item" key={item.evidence_id}>
            <div className="item-title">{item.claim}</div>
            <div className="item-meta">
              {item.source_title}
              {item.page ? ` · page ${item.page}` : ""}
              {item.section ? ` · ${item.section}` : ""}
              {item.evidence_type ? ` · ${item.evidence_type}` : ""}
            </div>
            <p className="muted">{item.quote_or_summary}</p>
            <div className="item-meta">
              {item.verification_method || "pending"} · confidence {item.verification_confidence ?? "n/a"}
              {item.matched_source ? ` · ${item.matched_source}` : ""}
            </div>
            <div className="item-actions">
              <span className={`badge ${item.verified ? "good" : "warn"}`}>
                {item.frozen
                  ? "frozen"
                  : run?.evidence_frozen
                    ? "not frozen"
                    : item.eligible_for_report
                      ? "report-ready"
                      : item.verified
                        ? "verified"
                        : "needs audit"}
              </span>
              <span className={`badge ${item.human_decision === "rejected" ? "warn" : item.human_decision === "accepted" ? "good" : ""}`}>
                {item.human_decision}
              </span>
              <button
                className="icon-button"
                title="Accept evidence"
                onClick={() => onDecision(item.evidence_id, "accepted")}
                disabled={busy || item.human_decision === "accepted"}
              >
                <Check size={14} />
              </button>
              <button
                className="icon-button danger"
                title="Reject evidence"
                onClick={() => onDecision(item.evidence_id, "rejected")}
                disabled={busy || item.human_decision === "rejected"}
              >
                <X size={14} />
              </button>
            </div>
          </article>
        ))}
        {!evidence.length && <p className="muted">暂无证据项</p>}
      </div>
    </section>
  );
}
