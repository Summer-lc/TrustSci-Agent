import { MessagesSquare } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function PerspectivePlanPanel({ run }: { run: ResearchRun | null }) {
  return (
    <section className="panel span-6">
      <h2><MessagesSquare size={16} /> 任务规划 / Planner Output</h2>
      <p className="muted compact">
        Planner Agent 会把你的科研问题拆成不同角色视角、检索问题和证据要求。
        It turns the research question into roles, search queries, and evidence requirements.
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
        {!run?.perspectives.length && <p className="muted">暂无任务规划 / No planner output yet.</p>}
      </div>
    </section>
  );
}
