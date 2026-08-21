import { ExternalLink, GitBranch, Search } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function BaselineBoard({
  run,
  busy,
  onDiscover,
  onVerify
}: {
  run: ResearchRun | null;
  busy: boolean;
  onDiscover: () => void;
  onVerify: (baselineId: string) => void;
}) {
  const intake = run?.baseline_intake;
  const candidates = [...(run?.baseline_candidates || [])].sort((a, b) => (b.baseline_priority_score || 0) - (a.baseline_priority_score || 0));

  return (
    <section className="panel span-12 baseline-board">
      <div className="panel-heading">
        <h2><GitBranch size={16} /> Baseline 可信来源</h2>
        <div className="actions">
          <span className="badge">{intake ? sourceLabel(intake.source_type) : "等待运行"}</span>
          <span className={`badge ${intake?.trust_level === "insufficient" ? "warn" : "good"}`}>{intake ? trustLabel(intake.trust_level) : "未生成"}</span>
        </div>
      </div>

      {intake ? (
        <article className="item">
          <div className="item-title">{intake.name || "Baseline intake"}</div>
          <div className="item-meta">
            来源 {sourceLabel(intake.source_type)} · 可信级别 {trustLabel(intake.trust_level)}
          </div>
          <p className="muted baseline-detail-copy">{intake.description}</p>
          <div className="metric-row">
            {intake.metrics.map((metric) => (
              <span className="badge" key={`${metric.name}-${metric.split || "all"}`}>
                {metric.name}: {metric.value}{metric.unit ? ` ${metric.unit}` : ""}
              </span>
            ))}
            {!intake.metrics.length && <span className="badge warn">无可比指标</span>}
          </div>
          {intake.limitations.map((item, index) => <p className="muted baseline-detail-copy" key={index}>限制：{item}</p>)}
        </article>
      ) : (
        <p className="muted">运行开始前请选择人工上传、AI 生成 demo baseline 或暂不提供 baseline。</p>
      )}

      <details className="legacy-section">
        <summary>Legacy 自动发现候选（已从主流程移除）</summary>
        <div className="actions">
          <span className="badge">{candidates.length} 个候选</span>
          <button className="secondary" onClick={onDiscover} disabled={busy}>
            <Search size={14} /> 手动发现
          </button>
        </div>
        <div className="list">
          {candidates.map((candidate) => (
            <article className="item" key={candidate.baseline_id}>
              <div className="item-title">{candidate.paper_title || "未关联论文"}</div>
              <div className="item-meta">
                {legacySourceLabel(candidate.code_source)} · {candidate.input_type || "未知输入"}
                {candidate.license ? ` · ${candidate.license}` : ""}
              </div>
              {candidate.code_url && (
                <a className="secondary link-button" href={candidate.code_url} target="_blank" rel="noreferrer">
                  <ExternalLink size={14} /> {candidate.code_url}
                </a>
              )}
              <div className="item-actions">
                <span className={`badge ${candidate.verified_repo ? "good" : candidate.reproduction_status === "suspicious" ? "warn" : ""}`}>
                  {reproductionLabel(candidate.reproduction_status)}
                </span>
                <span className="badge">{repoTypeLabel(candidate.repo_type || "unknown")}</span>
                <span className="badge">优先级 {(candidate.baseline_priority_score || 0).toFixed(2)}</span>
                <button className="secondary" onClick={() => onVerify(candidate.baseline_id)} disabled={busy}>
                  验证仓库
                </button>
              </div>
              {candidate.risks.length > 0 && <p className="muted baseline-detail-copy">风险：{candidate.risks.join("; ")}</p>}
            </article>
          ))}
          {!candidates.length && <p className="muted">主流程不再自动挖掘 baseline；这里仅保留旧调试入口。</p>}
        </div>
      </details>
    </section>
  );
}

function sourceLabel(source: string) {
  if (source === "manual_upload") return "人工上传";
  if (source === "ai_generated") return "AI 生成 demo";
  return "未提供";
}

function trustLabel(level: string) {
  if (level === "user_provided") return "用户提供";
  if (level === "runnable_demo") return "demo 可运行";
  return "不足";
}

function legacySourceLabel(source: string) {
  if (source === "github_search") return "GitHub 搜索";
  if (source === "papers_with_code") return "Papers with Code";
  if (source === "prior_art") return "已有工作";
  if (source === "pdf") return "PDF";
  return source || "未知来源";
}

function reproductionLabel(status: string) {
  if (status === "verified") return "已验证";
  if (status === "pending") return "待验证";
  if (status === "suspicious") return "可疑";
  if (status === "failed") return "失败";
  return status || "未知";
}

function repoTypeLabel(type: string) {
  if (type === "model_code") return "模型代码";
  if (type === "dataset_only") return "仅数据集";
  if (type === "docs_only") return "仅文档";
  if (type === "empty") return "空仓库";
  if (type === "unknown") return "未知类型";
  return type;
}
