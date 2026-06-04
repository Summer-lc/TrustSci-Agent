import { FolderArchive } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function WorkspacePanel({ run }: { run: ResearchRun | null }) {
  const artifacts = run?.workspace_artifacts || {};
  const entries = Object.entries(artifacts);

  return (
    <section className="panel span-6">
      <h2><FolderArchive size={16} /> Research Workspace</h2>
      {run?.workspace_path ? (
        <div className="list">
          <article className="item">
            <div className="item-title">{run.workspace_path}</div>
            <div className="item-meta">{entries.length} workspace artifacts</div>
          </article>
          {entries.slice(0, 6).map(([name, path]) => (
            <article className="item compact" key={name}>
              <div className="item-title">{name}</div>
              <div className="item-meta">{path}</div>
            </article>
          ))}
        </div>
      ) : (
        <p className="muted">暂无工作区</p>
      )}
    </section>
  );
}
