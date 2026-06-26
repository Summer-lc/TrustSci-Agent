import { CheckCircle2, ClipboardCheck, FileText, RefreshCw } from "lucide-react";
import { ResearchRun } from "../../lib/api";

type Props = {
  run: ResearchRun | null;
  busy?: boolean;
  onContinueRun: () => void;
  onRebuildReport: () => void;
};

type ChecklistItem = {
  title: string;
  subtitle: string;
  detail: string;
  status: "done" | "todo" | "warn" | "optional";
};

export function ReviewChecklistPanel({ run, busy = false, onContinueRun, onRebuildReport }: Props) {
  const paperStats = countDecisions(run?.papers || []);
  const evidenceStats = countDecisions(run?.evidence || []);
  const citationFrozen = Boolean(run?.citation_frozen);
  const evidenceFrozen = Boolean(run?.evidence_frozen);
  const hasReport = Boolean(run?.report);
  const unsupportedClaims = run?.claim_audit?.unsupported ?? 0;
  const running = run?.status === "running" || run?.status === "created";
  const completed = run?.status === "completed";
  const paused = run?.status === "paused";
  const guided = run?.constraints.workflow_mode === "guided";
  const autoCompleted = run?.constraints.workflow_mode === "auto" && completed;
  const canContinue =
    Boolean(run) &&
    paused &&
    ((run?.current_stage === "awaiting_citation_review" && citationFrozen) ||
      (run?.current_stage === "awaiting_evidence_review" && evidenceFrozen));
  const canRebuild = Boolean(run && completed && citationFrozen && evidenceFrozen);
  const nextAction = getNextAction(run, citationFrozen, evidenceFrozen, hasReport, unsupportedClaims);
  const citationReviewStatus = citationFrozen ? "done" : guided && paused ? "warn" : autoCompleted ? "optional" : "todo";
  const citationFreezeStatus = citationFrozen ? "done" : guided && paused ? "todo" : autoCompleted ? "optional" : "todo";
  const evidenceReviewStatus = evidenceFrozen ? "done" : guided && paused ? "warn" : autoCompleted ? "optional" : "todo";
  const evidenceFreezeStatus = evidenceFrozen ? "done" : guided && paused ? "todo" : autoCompleted ? "optional" : "todo";
  const claimStatus = run?.claim_audit
    ? unsupportedClaims > 0
      ? autoCompleted
        ? "optional"
        : "warn"
      : "done"
    : "todo";
  const reportStatus = hasReport
    ? citationFrozen && evidenceFrozen
      ? "done"
      : autoCompleted
        ? "optional"
        : "todo"
    : "todo";

  const items: ChecklistItem[] = [
    {
      title: "1. 工作流完成",
      subtitle: "Workflow completed",
      detail: run
        ? `${run.status} / ${run.current_stage || "idle"}，进度 ${Math.round((run.progress || 0) * 100)}%`
        : "先启动一个科研工作流 / Start a workflow first.",
      status: completed ? "done" : running ? "warn" : "todo"
    },
    {
      title: "2. 审核引用",
      subtitle: "Review citations",
      detail: `论文 ${paperStats.total} 篇：accepted ${paperStats.accepted}, rejected ${paperStats.rejected}, pending ${paperStats.pending}.`,
      status: citationReviewStatus
    },
    {
      title: "3. 冻结引用集",
      subtitle: "Freeze citation set",
      detail: citationFrozen
        ? `已冻结 ${run?.frozen_paper_ids.length || 0} 篇引用 / Frozen citations are locked for report generation.`
        : autoCompleted
          ? "Auto 模式已生成报告；如需人工修订，再审核并冻结引用。Auto already generated a report; freeze only if you want manual curation."
          : "在 Citation Verifier 中确认 √/× 后点击“冻结” / Approve or reject papers, then freeze.",
      status: citationFreezeStatus
    },
    {
      title: "4. 审核证据",
      subtitle: "Review evidence",
      detail: `证据 ${evidenceStats.total} 条：accepted ${evidenceStats.accepted}, rejected ${evidenceStats.rejected}, pending ${evidenceStats.pending}.`,
      status: evidenceReviewStatus
    },
    {
      title: "5. 冻结证据集",
      subtitle: "Freeze evidence set",
      detail: evidenceFrozen
        ? `已冻结 ${run?.frozen_evidence_ids.length || 0} 条证据 / Frozen evidence will be used as report support.`
        : autoCompleted
          ? "Auto 模式已生成报告；如需人工修订，再审核并冻结证据。Auto already generated a report; freeze only if you want manual curation."
          : "在 Evidence Board 中确认证据后点击“冻结” / Audit evidence items, then freeze.",
      status: evidenceFreezeStatus
    },
    {
      title: "6. 检查结论支持",
      subtitle: "Inspect claim audit",
      detail: run?.claim_audit
        ? `unsupported ${unsupportedClaims}, weak ${run.claim_audit.weakly_supported}, support score ${run.claim_audit.support_score}.`
        : "报告生成后检查 Claim Audit / Inspect claim support after report generation.",
      status: claimStatus
    },
    {
      title: "7. 重建并导出报告",
      subtitle: "Rebuild and export report",
      detail: hasReport
        ? "冻结后的 citation/evidence 修改完成后，重新生成报告再导出 Markdown/JSON。"
        : "等待报告生成，或在冻结 citation/evidence 后重建报告。",
      status: reportStatus
    }
  ];

  return (
    <section className="panel span-12">
      <div className="panel-heading">
        <h2><ClipboardCheck size={16} /> 审核清单 / Review Checklist</h2>
        <div className="actions">
          <span className={`badge ${autoCompleted || canRebuild ? "good" : paused ? "warn" : ""}`}>
            {paused
              ? "paused for review"
              : autoCompleted
                ? "auto completed"
                : canRebuild
                  ? "ready to rebuild"
                  : "workflow pending"}
          </span>
          <button className="secondary" onClick={onContinueRun} disabled={busy || !canContinue}>
            继续下一步 / Continue
          </button>
          <button className="secondary" onClick={onRebuildReport} disabled={busy || !canRebuild}>
            <RefreshCw size={14} /> 重建报告 / Rebuild
          </button>
        </div>
      </div>

      <div className="callout">
        <strong>下一步 / Next action</strong>
        <p>{nextAction}</p>
        <p className="muted compact">
          Auto 会先自动跑完整条科研链路；Guided 会在 citation/evidence 审核点暂停，人工点击 √/× 和 freeze 后才能继续。
          Auto runs end-to-end; Guided pauses at citation/evidence review gates before continuing.
        </p>
      </div>

      <div className="review-checklist">
        {items.map((item) => (
          <article className={`review-item ${item.status}`} key={item.title}>
            <div className="review-icon">
              {item.status === "done" ? <CheckCircle2 size={17} /> : <FileText size={17} />}
            </div>
            <div>
              <div className="item-title">{item.title}</div>
              <div className="item-meta">{item.subtitle}</div>
              <p className="muted compact">{item.detail}</p>
            </div>
            <span className={`badge ${item.status === "done" ? "good" : item.status === "warn" ? "warn" : ""}`}>
              {item.status === "done"
                ? "完成 Done"
                : item.status === "warn"
                  ? "需审核 Review"
                  : item.status === "optional"
                    ? "可选 Optional"
                    : "待处理 To do"}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

function countDecisions(items: Array<{ human_decision: "pending" | "accepted" | "rejected" }>) {
  return {
    total: items.length,
    accepted: items.filter((item) => item.human_decision === "accepted").length,
    rejected: items.filter((item) => item.human_decision === "rejected").length,
    pending: items.filter((item) => item.human_decision === "pending").length
  };
}

function getNextAction(
  run: ResearchRun | null,
  citationFrozen: boolean,
  evidenceFrozen: boolean,
  hasReport: boolean,
  unsupportedClaims: number
) {
  if (!run) return "先启动一个 workflow。Start a workflow, then review citations and evidence before exporting.";
  if (run.status === "running" || run.status === "created") {
    return `等待当前阶段完成：${run.current_stage || "running"}。Wait for the current stage before manual review.`;
  }
  if (run.status === "paused" && run.current_stage === "awaiting_citation_review") {
    return citationFrozen
      ? "引用已冻结，可以点击 Continue 生成 evidence ledger。Citations are frozen; click Continue to build the evidence ledger."
      : "当前停在 citation 审核点：请在 Citation Verifier 中接受/拒绝论文并 Freeze。Review citations, then freeze before continuing.";
  }
  if (run.status === "paused" && run.current_stage === "awaiting_evidence_review") {
    return evidenceFrozen
      ? "证据已冻结，可以点击 Continue 生成假设、实验计划和报告。Evidence is frozen; click Continue to generate hypotheses, experiment plan, and report."
      : "当前停在 evidence 审核点：请在 Evidence Board 中接受/拒绝证据并 Freeze。Review evidence, then freeze before continuing.";
  }
  if (run.status === "failed") {
    return "先查看 Workflow errors 和运行日志。Inspect workflow errors before continuing.";
  }
  if (run.constraints.workflow_mode === "auto" && run.status === "completed") {
    if (hasReport && unsupportedClaims > 0) {
      return "Auto 已完成。Citation/Evidence 人工审核是可选后处理；建议先查看 Claim Audit 的 unsupported 项。Auto completed; manual review is optional, but inspect unsupported claims first.";
    }
    return "Auto 已完成并生成报告。Citation/Evidence 审核与 freeze 是可选后处理。Auto completed; citation/evidence review and freeze are optional post-processing.";
  }
  if (!citationFrozen) {
    return "先到 Citation Verifier 审核论文引用，点击 √/× 后冻结。Review paper citations, then freeze the citation set.";
  }
  if (!evidenceFrozen) {
    return "再到 Evidence Board 审核证据，点击 √/× 后冻结。Review evidence items, then freeze the evidence set.";
  }
  if (hasReport && unsupportedClaims > 0) {
    return "检查 Claim Audit 中 unsupported 的结论，必要时补证据或拒绝弱证据后重建报告。Inspect unsupported claims, adjust evidence, then rebuild.";
  }
  if (hasReport) {
    return "可以重建报告并导出 Markdown/JSON。You can rebuild and export the final report.";
  }
  return "citation/evidence 已冻结，下一步生成或重建报告。Citation and evidence are frozen; generate or rebuild the report.";
}
