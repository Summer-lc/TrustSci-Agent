import { MessagesSquare } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function PerspectivePlanPanel({ run }: { run: ResearchRun | null }) {
  return (
    <section className="panel span-12">
      <h2><MessagesSquare size={16} /> 任务规划</h2>
      <p className="muted compact">
        Planner Agent 会把科研问题拆成不同角色视角、检索问题和证据要求。
      </p>
      <div className="list">
        {(run?.perspectives || []).slice(0, 5).map((item) => (
          <article className="item" key={item.perspective}>
            <div className="item-title">{item.role}</div>
            <div className="item-meta">{item.perspective}</div>
            <p className="muted">{item.question}</p>
            <div className="item-meta">{item.search_query}</div>
          </article>
        ))}
        {!run?.perspectives.length && <p className="muted">暂无任务规划。</p>}
      </div>
    </section>
  );
}
