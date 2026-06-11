import { BookOpen, ExternalLink, FileText } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function LiteratureBoard({ run }: { run: ResearchRun | null }) {
  const papers = run?.papers || [];
  const sourceCounts = papers.reduce<Record<string, number>>((acc, paper) => {
    const source = paper.source_api || "unknown";
    acc[source] = (acc[source] || 0) + 1;
    return acc;
  }, {});
  const verified = papers.filter((paper) => paper.verification_status === "verified").length;

  return (
    <section className="panel span-8">
      <div className="panel-heading">
        <h2><BookOpen size={16} /> Literature Board</h2>
        <div className="actions">
          <span className="badge">{papers.length} papers</span>
          <span className={`badge ${verified ? "good" : "warn"}`}>verified {verified}</span>
        </div>
      </div>
      <div className="metric-row">
        {Object.entries(sourceCounts).map(([source, count]) => (
          <span className="badge" key={source}>{source} {count}</span>
        ))}
        {!papers.length && <span className="badge warn">waiting for literature search</span>}
      </div>
      <div className="list">
        {papers.slice(0, 8).map((paper) => (
          <article className="item" key={paper.paper_id}>
            <div className="item-title">{paper.title}</div>
            <div className="item-meta">
              {paper.year || paper.publication_date || "n.d."}
              {paper.venue ? ` · ${paper.venue}` : ""}
              {paper.authors.length ? ` · ${paper.authors.slice(0, 3).join(", ")}` : ""}
            </div>
            <div className="item-meta">
              {paper.source_api || "unknown"} · DOI {paper.doi || "N/A"}
              {paper.arxiv_id ? ` · arXiv ${paper.arxiv_id}` : ""}
              {paper.cited_by_count !== undefined ? ` · cited ${paper.cited_by_count}` : ""}
            </div>
            {paper.abstract && <p className="muted">{paper.abstract.slice(0, 220)}{paper.abstract.length > 220 ? "..." : ""}</p>}
            <div className="item-actions">
              <span className={`badge ${paper.verification_status === "verified" ? "good" : "warn"}`}>
                {paper.verification_status}
              </span>
              <span className={`badge ${paper.report_eligible ? "good" : "warn"}`}>
                {paper.report_eligible ? "reference-ready" : "audit-only"}
              </span>
              {paper.source_url && (
                <a className="secondary link-button" href={paper.source_url} target="_blank" rel="noreferrer">
                  <ExternalLink size={14} /> Source
                </a>
              )}
              {paper.pdf_url && (
                <a className="secondary link-button" href={paper.pdf_url} target="_blank" rel="noreferrer">
                  <FileText size={14} /> PDF
                </a>
              )}
            </div>
          </article>
        ))}
        {!papers.length && <p className="muted">暂无文献候选</p>}
      </div>
    </section>
  );
}
