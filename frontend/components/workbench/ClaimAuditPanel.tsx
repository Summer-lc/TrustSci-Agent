import { ShieldCheck } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function ClaimAuditPanel({ run }: { run: ResearchRun | null }) {
  const audit = run?.claim_audit;
  const items = audit?.items || [];

  return (
    <section className="panel span-6">
      <div className="panel-heading">
        <h2><ShieldCheck size={16} /> 结论核验</h2>
        <span className={`badge ${audit && audit.unsupported === 0 ? "good" : "warn"}`}>
          {audit ? `支持分 ${audit.support_score}` : "待生成"}
        </span>
      </div>

      {audit ? (
        <>
          <div className="metric-row">
            <span className="badge good">已支持 {audit.supported}</span>
            <span className="badge">弱支持 {audit.weakly_supported}</span>
            <span className={`badge ${audit.unsupported ? "warn" : "good"}`}>不支持 {audit.unsupported}</span>
          </div>
          <div className="list">
            {items.slice(0, 6).map((item) => (
              <article className="item" key={item.claim_id}>
                <div className="item-title">{item.claim}</div>
                <div className="item-meta">
                  {item.claim_id} · 置信度 {item.confidence}
                </div>
                <p className="muted">{item.reason}</p>
                <div className="item-actions">
                  <span className={`badge ${item.status === "supported" ? "good" : item.status === "unsupported" ? "warn" : ""}`}>
                    {claimStatusLabel(item.status)}
                  </span>
                  <span className="badge">
                    证据 {item.matched_evidence_ids.length ? item.matched_evidence_ids.join(", ") : "无"}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </>
      ) : (
        <p className="muted">结论核验尚未生成。</p>
      )}
    </section>
  );
}

function claimStatusLabel(status: string) {
  if (status === "supported") return "已支持";
  if (status === "weakly_supported") return "弱支持";
  if (status === "unsupported") return "不支持";
  return status;
}
