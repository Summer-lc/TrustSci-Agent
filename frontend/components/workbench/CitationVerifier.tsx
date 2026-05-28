import { ShieldCheck } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function CitationVerifier({ run }: { run: ResearchRun | null }) {
  return (
    <section className="panel span-6">
      <h2><ShieldCheck size={16} /> Citation Verifier</h2>
      <div className="list">
        {(run?.papers || []).map((paper) => (
          <article className="item" key={paper.paper_id}>
            <div className="item-title">{paper.title}</div>
            <div className="item-meta">{paper.year || "n.d."} · DOI {paper.doi || "N/A"}</div>
            <span className={`badge ${paper.verification_status === "verified" ? "good" : "warn"}`}>
              {paper.verification_status}
            </span>
          </article>
        ))}
        {!run?.papers.length && <p className="muted">暂无候选论文</p>}
      </div>
    </section>
  );
}

