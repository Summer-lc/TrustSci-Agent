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
            <div className="item-meta">{item.source_title}</div>
            <p className="muted">{item.quote_or_summary}</p>
            <span className={`badge ${item.verified ? "good" : "warn"}`}>
              {item.verified ? "verified" : "needs audit"}
            </span>
          </article>
        ))}
        {!run?.evidence.length && <p className="muted">暂无证据项</p>}
      </div>
    </section>
  );
}

