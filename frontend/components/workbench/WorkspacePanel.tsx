import { FolderArchive } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function WorkspacePanel({ run }: { run: ResearchRun | null }) {
  const artifacts = run?.workspace_artifacts || {};
  const entries = Object.entries(artifacts);

  return (
    <section className="panel span-12 workspace-panel">
      <h2><FolderArchive size={16} /> 工作区文件 / Research Workspace</h2>
      {run?.workspace_path ? (
        <details className="workspace-details">
          <summary>
            <span>{run.workspace_path}</span>
            <span className="badge">{entries.length} artifacts</span>
          </summary>
          <div className="list workspace-artifacts">
            {entries.map(([name, path]) => (
              <article className="item compact" key={name}>
                <div className="item-title">{name}</div>
                <div className="item-meta">{path}</div>
              </article>
            ))}
          </div>
        </details>
      ) : (
        <p className="muted">暂无工作区 / No workspace yet.</p>
      )}
    </section>
  );
}
