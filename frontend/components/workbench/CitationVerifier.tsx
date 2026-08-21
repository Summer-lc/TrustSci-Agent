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
        <h2><ShieldCheck size={16} /> 引用核验</h2>
        <div className="actions">
          <span className={`badge ${run?.citation_frozen ? "good" : "warn"}`}>
            {run?.citation_frozen ? `已冻结 ${frozenCount}` : "待冻结"}
          </span>
          {run?.citation_frozen ? (
            <button className="secondary" onClick={onUnfreeze} disabled={busy || !run}>
              <RotateCcw size={14} /> 解冻
            </button>
          ) : (
            <button className="secondary" onClick={onFreeze} disabled={busy || !run || !run.papers.length}>
              <Lock size={14} /> 冻结
            </button>
          )}
        </div>
      </div>
      {report && (
        <div className="item compact">
          <div className="item-meta">
            已核验 {report.verified}/{report.total} · 完整性 {report.integrity_score}
          </div>
        </div>
      )}
      <div className="list">
        {(run?.papers || []).map((paper) => (
          <article className="item" key={paper.paper_id}>
            <div className="item-title">{paper.title}</div>
            <div className="item-meta">
              {paper.year || "未知年份"} · {paper.source_api || "未知来源"} · DOI {paper.doi || "无"}
            </div>
            <div className="item-meta">
              {paper.verification_method || "待核验"} · 置信度 {paper.verification_confidence ?? "n/a"}
              {paper.matched_source ? ` · ${paper.matched_source}` : ""}
            </div>
            <div className="item-actions">
              <span className={`badge ${paper.verification_status === "verified" ? "good" : "warn"}`}>
                {paper.frozen ? "已冻结" : paper.report_eligible ? "可进报告" : "仅审计"}
              </span>
              <span className={`badge ${paper.human_decision === "rejected" ? "warn" : paper.human_decision === "accepted" ? "good" : ""}`}>
                {decisionLabel(paper.human_decision)}
              </span>
              <span className="badge">{verificationLabel(paper.verification_status)}</span>
              <button
                className="icon-button"
                title="接受引用"
                onClick={() => onDecision(paper.paper_id, "accepted")}
                disabled={busy || paper.human_decision === "accepted" || paper.verification_status !== "verified"}
              >
                <Check size={14} />
              </button>
              <button
                className="icon-button danger"
                title="拒绝引用"
                onClick={() => onDecision(paper.paper_id, "rejected")}
                disabled={busy || paper.human_decision === "rejected"}
              >
                <X size={14} />
              </button>
            </div>
          </article>
        ))}
        {!run?.papers.length && <p className="muted">暂无候选论文。</p>}
      </div>
    </section>
  );
}

function decisionLabel(decision: string) {
  if (decision === "accepted") return "已接受";
  if (decision === "rejected") return "已拒绝";
  return "待处理";
}

function verificationLabel(status: string) {
  if (status === "verified") return "已核验";
  if (status === "hallucinated") return "疑似幻觉";
  if (status === "partial") return "部分匹配";
  if (status === "suspicious") return "可疑";
  return status || "未知";
}
