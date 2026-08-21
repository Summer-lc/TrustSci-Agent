import type { ResearchRun } from "../../lib/api";

const VERDICT_BADGE: Record<string, string> = {
  novel: "good",
  transfer_applicability: "warn",
  already_done: "warn",
  dataset_only: "good",
  similar_work: "warn",
};

const VERDICT_LABEL: Record<string, string> = {
  novel: "新颖",
  transfer_applicability: "迁移式创新",
  already_done: "已有相同工作",
  dataset_only: "只是数据集",
  similar_work: "已有相近工作",
};

const REASON_LABEL: Record<string, string> = {
  "no verified external model baseline": "没有找到已验证的外部模型 baseline",
  "only 1 comparable model(s) (need >=2)": "当前只有 1 个可比较模型，需要至少 2 个",
  "all candidates are dataset/docs/empty repos": "候选基本都是数据集、文档或空仓库",
  "baseline does not match seismic task domain": "baseline 与当前地震任务不匹配",
  "repo reproducibility score below 0.6": "仓库可复现评分低于 0.6",
};

export function FeedbackLoopPanel({ run }: { run: ResearchRun }) {
  const verdict = run.novelty_verdict;
  const gate = run.baseline_gate_status;
  const noveltyStatus =
    run.novelty_status && run.novelty_status !== "not_checked" ? run.novelty_status : "pending";
  const comparisonGrade = gate?.comparison_grade ?? "pending";
  const rewriteRound = Math.min(run.macro_round ?? 0, 1);

  return (
    <section className="panel span-12 code-panel feedback-panel">
      <div className="panel-heading">
        <h2>反馈循环</h2>
        <div className="badges">
          {verdict ? (
            <span className={`badge ${VERDICT_BADGE[verdict.verdict] ?? "warn"}`}>
              新颖性：{VERDICT_LABEL[verdict.verdict] ?? verdict.verdict}
            </span>
          ) : (
            <span className="badge">等待新颖性检查</span>
          )}
          <span className={`badge ${statusBadgeClass(noveltyStatus, "ok")}`}>
            {noveltyStatus === "ok" ? "新颖性可继续" : noveltyStatus === "pending" ? "未检查" : noveltyStatus}
          </span>
          <span className={`badge ${statusBadgeClass(comparisonGrade, "research")}`}>
            {comparisonGrade === "research" ? "科研级对比" : comparisonGrade === "degraded" ? "降级对比" : "等待 baseline 门"}
          </span>
        </div>
      </div>

      <div className="code-kv">
        <span>
          <strong>新颖性重跑</strong>
          {run.novelty_round ?? 0}
        </span>
        <span>
          <strong>Baseline 重搜</strong>
          {run.re_search_round ?? 0}
        </span>
        <span title="Top1 的代码实验失败或明显输给 baseline 时，最多允许 LLM 从方法/模型方案层面重写一次。">
          <strong>Top1 方案重写</strong>
          {rewriteRound}/1
        </span>
        <span>
          <strong>切换 Top2</strong>
          {run.switchback_used ? "已使用" : "未使用"}
        </span>
        <span>
          <strong>证据已变化</strong>
          {run.evidence_changed ? "是" : "否"}
        </span>
        <span>
          <strong>假设已变化</strong>
          {run.hypothesis_changed ? "是" : "否"}
        </span>
      </div>

      <p className="muted compact">
        Top1 方案重写只给一次机会：如果 Top1 的代码实验失败或明显低于 baseline，系统会让 LLM 重写一次方法/模型方案；若仍不理想，才考虑切换 Top2 或接受负结果。
      </p>

      {gate ? (
        <div className="badges">
          <span className="badge">外部已验证模型 {gate.external_verified_model_baselines}</span>
          <span className="badge">可比较模型 {gate.comparable_count}</span>
          <span className={`badge ${gate.research_gate_passed ? "good" : "warn"}`}>
            科研门 {gate.research_gate_passed ? "通过" : "未通过"}
          </span>
        </div>
      ) : (
        <p className="muted compact">等待 baseline 质量门结果。</p>
      )}

      {gate && gate.insufficient_reasons.length > 0 && (
        <ul className="notes">
          {gate.insufficient_reasons.map((reason, index) => (
            <li key={index}>{REASON_LABEL[reason] ?? reason}</li>
          ))}
        </ul>
      )}
      {verdict?.reasoning && <p className="muted compact">新颖性判断依据：{verdict.reasoning}</p>}
    </section>
  );
}

function statusBadgeClass(value: string, goodValue: string) {
  if (value === goodValue) return "good";
  if (value === "pending") return "";
  return "warn";
}
