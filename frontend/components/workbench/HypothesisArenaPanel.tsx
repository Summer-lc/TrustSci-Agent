import { Trophy } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function HypothesisArenaPanel({ run }: { run: ResearchRun | null }) {
  const arena = run?.arena_result;
  if (!arena) {
    return (
      <section className="panel span-8">
        <div className="panel-heading"><h2><Trophy size={16} /> 假设竞技场</h2></div>
        <p className="muted">等待假设竞技完成。地震任务会自动触发这一阶段。</p>
      </section>
    );
  }
  const sorted = [...(arena.candidates || [])].sort((a, b) => (a.rank || 0) - (b.rank || 0));
  return (
    <section className="panel span-8">
      <div className="panel-heading">
        <h2><Trophy size={16} /> 假设竞技场</h2>
        <div className="actions">
          <span className="badge">{arena.mode}</span>
          <span className="badge">{arena.arena_level}</span>
        </div>
      </div>
      <div className="item">
        <div className="item-title">Top1（已选中）：{arena.selected_for_experiment}</div>
        {arena.switchback_candidate ? <div className="muted">备用 Top2：{arena.switchback_candidate}</div> : null}
      </div>
      <div className="list">
        {sorted.map((candidate) => (
          <article className="item" key={candidate.hypothesis_id}>
            <div className="item-title">
              #{candidate.rank} {candidate.hypothesis_id}{candidate.is_user_idea ? "（用户想法）" : ""}
            </div>
            <div className="muted">{candidate.statement}</div>
            <div className="item-actions">
              <span className={`badge ${candidate.hypothesis_id === arena.selected_for_experiment ? "good" : ""}`}>
                评分 {candidate.weighted_score.toFixed(1)}
              </span>
            </div>
          </article>
        ))}
      </div>
      {arena.ablation_design && arena.ablation_design.length > 0 && (
        <div className="item">
          <div className="item-title">消融设计（创意精修）</div>
          {arena.ablation_design.map((item) => (
            <div className="muted" key={item.challenge_id}>
              {item.challenge_id}：测试 {item.tests_innovation_point}；预期洞察：{item.expected_insight}；来源：{item.derivation_from_main}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
