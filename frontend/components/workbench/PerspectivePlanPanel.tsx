import { MessagesSquare } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function PerspectivePlanPanel({ run }: { run: ResearchRun | null }) {
  return (
    <section className="panel span-6">
      <h2><MessagesSquare size={16} /> Perspective Planner</h2>
      <div className="list">
        {(run?.perspectives || []).slice(0, 5).map((item) => (
          <article className="item" key={item.perspective}>
            <div className="item-title">{item.role}</div>
            <div className="item-meta">{item.perspective}</div>
            <p className="muted">{item.question}</p>
            <div className="item-meta">{item.search_query}</div>
          </article>
        ))}
        {!run?.perspectives.length && <p className="muted">暂无多视角规划</p>}
      </div>
    </section>
  );
}
