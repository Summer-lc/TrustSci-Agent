import { ShieldCheck } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function CitationVerifier({ run }: { run: ResearchRun | null }) {
  const report = run?.citation_report;
  return (
    <section className="panel span-6">
      <h2><ShieldCheck size={16} /> Citation Verifier</h2>
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
            <span className={`badge ${paper.verification_status === "verified" ? "good" : "warn"}`}>
              {paper.verification_status}{paper.report_eligible ? " · report" : " · audit"}
            </span>
          </article>
        ))}
        {!run?.papers.length && <p className="muted">暂无候选论文</p>}
      </div>
    </section>
  );
}
