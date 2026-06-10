import { ShieldCheck } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function ClaimAuditPanel({ run }: { run: ResearchRun | null }) {
  const audit = run?.claim_audit;
  const items = audit?.items || [];

  return (
    <section className="panel span-6">
      <div className="panel-heading">
        <h2><ShieldCheck size={16} /> Claim Audit</h2>
        <span className={`badge ${audit && audit.unsupported === 0 ? "good" : "warn"}`}>
          {audit ? `support ${audit.support_score}` : "pending"}
        </span>
      </div>

      {audit ? (
        <>
          <div className="metric-row">
            <span className="badge good">supported {audit.supported}</span>
            <span className="badge">weak {audit.weakly_supported}</span>
            <span className={`badge ${audit.unsupported ? "warn" : "good"}`}>unsupported {audit.unsupported}</span>
          </div>
          <div className="list">
            {items.slice(0, 6).map((item) => (
              <article className="item" key={item.claim_id}>
                <div className="item-title">{item.claim}</div>
                <div className="item-meta">
                  {item.claim_id} · confidence {item.confidence}
                </div>
                <p className="muted">{item.reason}</p>
                <div className="item-actions">
                  <span className={`badge ${item.status === "supported" ? "good" : item.status === "unsupported" ? "warn" : ""}`}>
                    {item.status}
                  </span>
                  <span className="badge">
                    evidence {item.matched_evidence_ids.length ? item.matched_evidence_ids.join(", ") : "none"}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </>
      ) : (
        <p className="muted">Claim audit 尚未生成</p>
      )}
    </section>
  );
}
