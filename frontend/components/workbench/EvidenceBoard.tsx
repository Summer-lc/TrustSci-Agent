import { FileSearch } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function EvidenceBoard({ run }: { run: ResearchRun | null }) {
  return (
    <section className="panel span-8">
      <h2><FileSearch size={16} /> Evidence Board</h2>
      <div className="list">
        {(run?.evidence || []).slice(0, 6).map((item) => (
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
            <span className={`badge ${item.verified ? "good" : "warn"}`}>
              {item.eligible_for_report ? "report-ready" : item.verified ? "verified" : "needs audit"}
            </span>
          </article>
        ))}
        {!run?.evidence.length && <p className="muted">暂无证据项</p>}
      </div>
    </section>
  );
}
