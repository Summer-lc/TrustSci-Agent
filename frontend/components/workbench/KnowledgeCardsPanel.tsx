import { LibraryBig } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function KnowledgeCardsPanel({ run }: { run: ResearchRun | null }) {
  return (
    <section className="panel span-6">
      <h2><LibraryBig size={16} /> 知识卡片</h2>
      <div className="list">
        {(run?.knowledge_cards || []).slice(0, 6).map((card) => (
          <article className="item" key={card.card_id}>
            <div className="item-title">{card.finding}</div>
            <div className="item-meta">
              {card.perspective} · 置信度 {card.confidence}
            </div>
            <p className="muted">{card.transferability}</p>
            <span className={`badge ${card.report_eligible ? "good" : "warn"}`}>
              {card.report_eligible ? "可进报告" : "仅审计"}
            </span>
          </article>
        ))}
        {!run?.knowledge_cards.length && <p className="muted">暂无知识卡片。</p>}
      </div>
    </section>
  );
}
