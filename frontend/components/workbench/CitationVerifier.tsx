import { Check, Lock, RotateCcw, ShieldCheck, X } from "lucide-react";
import { ResearchRun } from "../../lib/api";

type PaperDecision = "pending" | "accepted" | "rejected";

type Props = {
  run: ResearchRun | null;
  busy?: boolean;
  onDecision: (paperId: string, decision: PaperDecision) => void;
  onFreeze: () => void;
  onUnfreeze: () => void;
};

export function CitationVerifier({ run, busy = false, onDecision, onFreeze, onUnfreeze }: Props) {
  const report = run?.citation_report;
  const frozenCount = run?.frozen_paper_ids.length || 0;
  return (
    <section className="panel span-6">
      <div className="panel-heading">
        <h2><ShieldCheck size={16} /> 引用核验 / Citation Verifier</h2>
        <div className="actions">
          <span className={`badge ${run?.citation_frozen ? "good" : "warn"}`}>
            {run?.citation_frozen ? `已冻结 / frozen ${frozenCount}` : "待冻结 / open"}
          </span>
          {run?.citation_frozen ? (
            <button className="secondary" onClick={onUnfreeze} disabled={busy || !run}>
              <RotateCcw size={14} /> 解冻 / Unfreeze
            </button>
          ) : (
            <button className="secondary" onClick={onFreeze} disabled={busy || !run || !run.papers.length}>
              <Lock size={14} /> 冻结 / Freeze
            </button>
          )}
        </div>
      </div>
      {report && (
        <div className="item compact">
          <div className="item-meta">
            verified {report.verified}/{report.total} · integrity {report.integrity_score}
          </div>
        </div>
      )}
      <div className="list">
        {(run?.papers || []).map((paper) => (
          <article className="item" key={paper.paper_id}>
            <div className="item-title">{paper.title}</div>
            <div className="item-meta">
              {paper.year || "n.d."} · {paper.source_api || "source"} · DOI {paper.doi || "N/A"}
            </div>
            <div className="item-meta">
              {paper.verification_method || "pending"} · confidence {paper.verification_confidence ?? "n/a"}
              {paper.matched_source ? ` · ${paper.matched_source}` : ""}
            </div>
            <div className="item-actions">
              <span className={`badge ${paper.verification_status === "verified" ? "good" : "warn"}`}>
                {paper.frozen ? "frozen" : paper.report_eligible ? "report" : "audit"}
              </span>
              <span className={`badge ${paper.human_decision === "rejected" ? "warn" : paper.human_decision === "accepted" ? "good" : ""}`}>
                {paper.human_decision}
              </span>
              <span className="badge">{paper.verification_status}</span>
              <button
                className="icon-button"
                title="接受引用 / Approve citation"
                onClick={() => onDecision(paper.paper_id, "accepted")}
                disabled={busy || paper.human_decision === "accepted" || paper.verification_status !== "verified"}
              >
                <Check size={14} />
              </button>
              <button
                className="icon-button danger"
                title="拒绝引用 / Reject citation"
                onClick={() => onDecision(paper.paper_id, "rejected")}
                disabled={busy || paper.human_decision === "rejected"}
              >
                <X size={14} />
              </button>
            </div>
          </article>
        ))}
        {!run?.papers.length && <p className="muted">暂无候选论文 / No candidate papers yet.</p>}
      </div>
    </section>
  );
}
