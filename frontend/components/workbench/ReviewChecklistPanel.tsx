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

  const items: ChecklistItem[] = [
    {
      title: "1. 工作流完成",
      detail: run
        ? `${statusLabel(run.status)} / ${run.current_stage || "空闲"}，进度 ${Math.round((run.progress || 0) * 100)}%`
        : "先启动一个科研工作流。",
      status: completed ? "done" : running ? "warn" : "todo"
    },
    {
      title: "2. 审核引用",
      detail: `论文 ${paperStats.total} 篇：已接受 ${paperStats.accepted}，已拒绝 ${paperStats.rejected}，待处理 ${paperStats.pending}。`,
      status: citationFrozen ? "done" : guided && paused ? "warn" : autoCompleted ? "optional" : "todo"
    },
    {
      title: "3. 冻结引用集",
      detail: citationFrozen
        ? `已冻结 ${run?.frozen_paper_ids.length || 0} 篇引用。`
        : "在“引用核验”中接受/拒绝论文后点击冻结。",
      status: citationFrozen ? "done" : guided && paused ? "todo" : autoCompleted ? "optional" : "todo"
    },
    {
      title: "4. 审核证据",
      detail: `证据 ${evidenceStats.total} 条：已接受 ${evidenceStats.accepted}，已拒绝 ${evidenceStats.rejected}，待处理 ${evidenceStats.pending}。`,
      status: evidenceFrozen ? "done" : guided && paused ? "warn" : autoCompleted ? "optional" : "todo"
    },
    {
      title: "5. 冻结证据集",
      detail: evidenceFrozen
        ? `已冻结 ${run?.frozen_evidence_ids.length || 0} 条证据。`
        : "在“证据板”中接受/拒绝证据后点击冻结。",
      status: evidenceFrozen ? "done" : guided && paused ? "todo" : autoCompleted ? "optional" : "todo"
    },
    {
      title: "6. 检查结论支持",
      detail: run?.claim_audit
        ? `不支持 ${unsupportedClaims}，弱支持 ${run.claim_audit.weakly_supported}，支持分 ${run.claim_audit.support_score}。`
        : "报告生成后会出现结论核验结果。",
      status: run?.claim_audit ? (unsupportedClaims > 0 ? "warn" : "done") : "todo"
    },
    {
      title: "7. 重建并导出报告",
      detail: hasReport ? "可以查看、重建或导出报告。" : "等待报告生成。",
      status: hasReport ? (citationFrozen && evidenceFrozen ? "done" : "optional") : "todo"
    }
  ];

  return (
    <section className="panel span-12">
      <div className="panel-heading">
        <h2><ClipboardCheck size={16} /> 审核清单</h2>
        <div className="actions">
          <span className={`badge ${autoCompleted || canRebuild ? "good" : paused ? "warn" : ""}`}>
            {paused
              ? "等待人工审核"
              : autoCompleted
                ? "自动流程已完成"
                : canRebuild
                  ? "可重建报告"
                  : "工作流进行中"}
          </span>
          <button className="secondary" onClick={onContinueRun} disabled={busy || !canContinue}>
            继续下一步
          </button>
          <button className="secondary" onClick={onRebuildReport} disabled={busy || !canRebuild}>
            <RefreshCw size={14} /> 重建报告
          </button>
        </div>
      </div>

      <div className="callout">
        <strong>下一步</strong>
        <p>{getNextAction(run, citationFrozen, evidenceFrozen, hasReport, unsupportedClaims)}</p>
        <p className="muted compact">
          自动模式会尽量端到端跑完；引导模式会在引用和证据审核点暂停。
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
              <p className="muted compact">{item.detail}</p>
            </div>
            <span className={`badge ${item.status === "done" ? "good" : item.status === "warn" ? "warn" : ""}`}>
              {statusText(item.status)}
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
  if (!run) return "先启动一个工作流。";
  if (run.status === "running" || run.status === "created") {
    return `等待当前阶段完成：${run.current_stage || "运行中"}。`;
  }
  if (run.status === "paused" && run.current_stage === "awaiting_citation_review") {
    return citationFrozen ? "引用已冻结，可以继续下一步。" : "当前停在引用审核点：请接受/拒绝论文并冻结引用。";
  }
  if (run.status === "paused" && run.current_stage === "awaiting_evidence_review") {
    return evidenceFrozen ? "证据已冻结，可以继续下一步。" : "当前停在证据审核点：请接受/拒绝证据并冻结证据。";
  }
  if (run.status === "failed") return "请先查看工作流错误。";
  if (run.constraints.workflow_mode === "auto" && run.status === "completed") {
    if (hasReport && unsupportedClaims > 0) return "自动流程已完成；建议先查看不支持的结论。";
    return "自动流程已完成；引用/证据人工审核是可选后处理。";
  }
  if (!citationFrozen) return "先审核并冻结引用。";
  if (!evidenceFrozen) return "再审核并冻结证据。";
  if (hasReport && unsupportedClaims > 0) return "检查不支持的结论，必要时调整证据后重建报告。";
  if (hasReport) return "可以重建或导出最终报告。";
  return "引用和证据已冻结，下一步生成或重建报告。";
}

function statusText(status: ChecklistItem["status"]) {
  if (status === "done") return "完成";
  if (status === "warn") return "需审核";
  if (status === "optional") return "可选";
  return "待处理";
}

function statusLabel(status: string) {
  if (status === "running") return "运行中";
  if (status === "created") return "已创建";
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "paused") return "暂停";
  return status;
}
