import { Activity, Waves } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function SeismicOverviewPanel({ run }: { run: ResearchRun | null }) {
  const intent = run?.intent;
  const idea = run?.idea_brief;
  const profile = run?.seismic_data_profile;
  return (
    <section className="panel span-4">
      <div className="panel-heading">
        <h2><Waves size={16} /> 地震任务概览</h2>
        <span className="badge"><Activity size={13} />{modeLabel(run?.mode || "discovery")}</span>
      </div>
      {intent && (
        <div className="item">
          <div className="item-title">意图识别</div>
          <div className="muted">模式：{modeLabel(String(intent.mode))}；置信度：{String(intent.confidence)}</div>
          <div className="muted">{intent.reason}</div>
        </div>
      )}
      {idea && (
        <div className="item">
          <div className="item-title">用户想法</div>
          <div className="muted">{idea.user_idea}</div>
          {idea.target_labels?.length ? <div className="muted">目标标签：{idea.target_labels.join(", ")}</div> : null}
          {idea.unknowns?.length ? <div className="muted">待确认：{idea.unknowns.join("; ")}</div> : null}
        </div>
      )}
      {profile && (
        <div className="item">
          <div className="item-title">地震数据画像</div>
          <div className="muted">
            {profile.num_events} 个事件；{Object.entries(profile.labels).map(([k, v]) => `${k}:${v}`).join(", ")}
          </div>
          <div className="muted">通道：{profile.channels.join("/")}</div>
          {profile.risks?.length ? <div className="muted">风险：{profile.risks.join("; ")}</div> : null}
        </div>
      )}
      {!intent && !idea && !profile && <p className="muted">等待意图识别、想法解析和地震数据画像完成。</p>}
    </section>
  );
}

function modeLabel(mode: string) {
  if (mode === "idea_refinement") return "创意精修";
  if (mode === "experiment_assistance") return "实验辅助";
  if (mode === "guided") return "引导模式";
  return "自动发现";
}
