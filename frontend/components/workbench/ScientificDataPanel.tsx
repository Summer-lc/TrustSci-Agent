import { BaselineResultCard, DatasetProfile, ResearchRun } from "../../lib/api";

export function ScientificDataPanel({
  run,
  profiles,
  baseline
}: {
  run: ResearchRun | null;
  profiles: DatasetProfile[];
  baseline: BaselineResultCard | null;
}) {
  const shownProfiles = run?.data_profiles?.length ? run.data_profiles : profiles;
  const shownBaseline = run?.baseline_result_card || baseline;

  return (
    <section className="panel span-6">
      <h2>科研数据</h2>
      <div className="list">
        {shownProfiles.slice(0, 4).map((profile) => (
          <article className="item" key={profile.name}>
            <div className="item-title">{profile.name}</div>
            <div className="item-meta">
              {profile.source} · {profile.rows ? `${profile.rows} 行` : profile.availability}
            </div>
            <p className="muted">{profile.target || "无目标字段"} · {profile.task_type}</p>
          </article>
        ))}
        {shownBaseline && (
          <article className="item">
            <div className="item-title">{shownBaseline.name}</div>
            <div className="item-meta">
              {Object.entries(shownBaseline.metrics).map(([key, value]) => `${key} ${value}`).join(" · ")}
            </div>
            <p className="muted">{shownBaseline.result_summary}</p>
          </article>
        )}
        {!shownProfiles.length && <p className="muted">暂无数据画像。</p>}
      </div>
    </section>
  );
}
