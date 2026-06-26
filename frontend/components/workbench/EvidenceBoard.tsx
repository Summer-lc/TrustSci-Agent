import { useMemo, useState } from "react";
import { Check, FileSearch, Lock, RotateCcw, X } from "lucide-react";
import { ResearchRun } from "../../lib/api";

type EvidenceDecision = "pending" | "accepted" | "rejected";
type EvidenceFilter = "all" | "report" | "frozen" | "accepted" | "rejected" | "unsupported";

type Props = {
  run: ResearchRun | null;
  busy?: boolean;
  onDecision: (evidenceId: string, decision: EvidenceDecision) => void;
  onFreeze: () => void;
  onUnfreeze: () => void;
};

export function EvidenceBoard({ run, busy = false, onDecision, onFreeze, onUnfreeze }: Props) {
  const [filter, setFilter] = useState<EvidenceFilter>("all");
  const evidence = run?.evidence || [];
  const frozenCount = run?.frozen_evidence_ids.length || 0;
  const matchedEvidenceIds = useMemo(
    () => new Set((run?.claim_audit?.items || []).flatMap((item) => item.matched_evidence_ids)),
    [run?.claim_audit?.items]
  );
  const filteredEvidence = evidence.filter((item) => {
    if (filter === "report") return item.eligible_for_report && item.human_decision !== "rejected";
    if (filter === "frozen") return item.frozen;
    if (filter === "accepted") return item.human_decision === "accepted";
    if (filter === "rejected") return item.human_decision === "rejected";
    if (filter === "unsupported") return item.eligible_for_report && !matchedEvidenceIds.has(item.evidence_id);
    return true;
  });
  const counts: Record<EvidenceFilter, number> = {
    all: evidence.length,
    report: evidence.filter((item) => item.eligible_for_report && item.human_decision !== "rejected").length,
    frozen: evidence.filter((item) => item.frozen).length,
    accepted: evidence.filter((item) => item.human_decision === "accepted").length,
    rejected: evidence.filter((item) => item.human_decision === "rejected").length,
    unsupported: evidence.filter((item) => item.eligible_for_report && !matchedEvidenceIds.has(item.evidence_id)).length
  };

  return (
    <section className="panel span-6">
      <div className="panel-heading">
        <h2><FileSearch size={16} /> 证据板 / Evidence Board</h2>
        <div className="actions">
          <span className={`badge ${run?.evidence_frozen ? "good" : "warn"}`}>
            {run?.evidence_frozen ? `已冻结 / frozen ${frozenCount}` : "待冻结 / open"}
          </span>
          {run?.evidence_frozen ? (
            <button className="secondary" onClick={onUnfreeze} disabled={busy || !run}>
              <RotateCcw size={14} /> 解冻 / Unfreeze
            </button>
          ) : (
            <button className="secondary" onClick={onFreeze} disabled={busy || !run || evidence.length === 0}>
              <Lock size={14} /> 冻结 / Freeze
            </button>
          )}
        </div>
      </div>
      <div className="segmented">
        {(["all", "report", "frozen", "accepted", "rejected", "unsupported"] as EvidenceFilter[]).map((key) => (
          <button
            key={key}
            className={filter === key ? "active" : ""}
            onClick={() => setFilter(key)}
          >
            {key} {counts[key]}
          </button>
        ))}
      </div>
      <div className="list">
        {filteredEvidence.slice(0, 8).map((item) => (
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
                title="接受证据 / Accept evidence"
                onClick={() => onDecision(item.evidence_id, "accepted")}
                disabled={busy || item.human_decision === "accepted"}
              >
                <Check size={14} />
              </button>
              <button
                className="icon-button danger"
                title="拒绝证据 / Reject evidence"
                onClick={() => onDecision(item.evidence_id, "rejected")}
                disabled={busy || item.human_decision === "rejected"}
              >
                <X size={14} />
              </button>
            </div>
          </article>
        ))}
        {!filteredEvidence.length && <p className="muted">当前筛选下暂无证据项 / No evidence under this filter.</p>}
      </div>
    </section>
  );
}
