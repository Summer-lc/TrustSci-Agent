import { Activity, BookOpenCheck, CheckCircle2, CircleDashed, FileText, ShieldCheck } from "lucide-react";

import { PaperPreviewResult, ResearchRun } from "../../lib/api";
import { PaperReaderPanel } from "./PaperReaderPanel";

type Paper = ResearchRun["papers"][number];
export type ContextTab = "paper" | "evidence" | "run";

export function ContextInspector({
  activeTab,
  run,
  paper,
  preview,
  loading,
  error,
  onTabChange,
  onRetryPreview,
}: {
  activeTab: ContextTab;
  run: ResearchRun | null;
  paper: Paper | null;
  preview: PaperPreviewResult | null;
  loading: boolean;
  error: string;
  onTabChange: (tab: ContextTab) => void;
  onRetryPreview: () => void;
}) {
  const tabs: Array<{ id: ContextTab; label: string; icon: typeof FileText }> = [
    { id: "paper", label: "文献", icon: FileText },
    { id: "evidence", label: "证据", icon: ShieldCheck },
    { id: "run", label: "运行", icon: Activity },
  ];

  return (
    <div className="context-inspector" aria-label="科研上下文">
      <div className="context-tabs" role="tablist" aria-label="科研上下文视图">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              className={activeTab === tab.id ? "active" : ""}
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => onTabChange(tab.id)}
            >
              <Icon size={14} /> {tab.label}
            </button>
          );
        })}
      </div>

      <div className="context-content" role="tabpanel">
        {activeTab === "paper" && (
          <PaperReaderPanel
            paper={paper}
            preview={preview}
            loading={loading}
            error={error}
            onRetryPreview={onRetryPreview}
          />
        )}
        {activeTab === "evidence" && <EvidenceContext run={run} paper={paper} />}
        {activeTab === "run" && <RunContext run={run} />}
      </div>
    </div>
  );
}

function EvidenceContext({ run, paper }: { run: ResearchRun | null; paper: Paper | null }) {
  if (!paper) {
    return <ContextEmpty icon={<BookOpenCheck size={22} />} text="选择一篇论文后，这里会显示其核验与报告资格。" />;
  }

  const linkedEvidence = run?.evidence.filter((item) => item.source_title === paper.title) || [];
  return (
    <section className="context-section">
      <div className="context-heading">
        <span className="context-kicker">当前论文</span>
        <h2>{paper.title}</h2>
        <p>{paper.venue || paper.source_api || "未知来源"} · {paper.year || paper.publication_date || "未知年份"}</p>
      </div>
      <div className="context-fact-grid">
        <ContextFact label="引用核验" value={verificationLabel(paper.verification_status)} good={paper.verification_status === "verified"} />
        <ContextFact label="报告资格" value={paper.report_eligible ? "可进入报告" : "仅供审计"} good={paper.report_eligible} />
        <ContextFact label="人工决策" value={decisionLabel(paper.human_decision)} good={paper.human_decision === "accepted"} />
        <ContextFact label="证据条目" value={`${linkedEvidence.length} 条`} good={linkedEvidence.length > 0} />
      </div>
      <div className="context-note">
        <ShieldCheck size={17} />
        <span>
          <strong>可追溯来源</strong>
          <small>{paper.doi ? `DOI ${paper.doi}` : paper.arxiv_id ? `arXiv ${paper.arxiv_id}` : "来源标识待补充"}</small>
        </span>
      </div>
      {paper.paper_role && (
        <div className="context-note subtle">
          <BookOpenCheck size={17} />
          <span><strong>论文角色</strong><small>{paperRoleLabel(paper.paper_role)}</small></span>
        </div>
      )}
    </section>
  );
}

function RunContext({ run }: { run: ResearchRun | null }) {
  if (!run) {
    return <ContextEmpty icon={<CircleDashed size={22} />} text="启动研究后，这里会显示实时阶段与最近执行记录。" />;
  }

  const recentSteps = [...run.steps].slice(-6).reverse();
  return (
    <section className="context-section">
      <div className="context-heading">
        <span className="context-kicker">执行透明度</span>
        <h2>{statusLabel(run.status, run.control_action)}</h2>
        <p>{stageLabel(run.current_stage)} · 已完成 {Math.round(run.progress || 0)}%</p>
      </div>
      <div className="run-progress" aria-label={`研究进度 ${Math.round(run.progress || 0)}%`}>
        <span style={{ width: `${Math.max(0, Math.min(100, run.progress || 0))}%` }} />
      </div>
      <div className="context-timeline">
        {recentSteps.map((step) => (
          <div className={`context-step ${step.status}`} key={`${step.name}-${step.summary}`}>
            {step.status === "completed" ? <CheckCircle2 size={15} /> : <CircleDashed size={15} />}
            <span><strong>{stageLabel(step.name)}</strong><small>{step.summary || statusLabel(step.status)}</small></span>
          </div>
        ))}
        {!recentSteps.length && <p className="muted">任务已创建，等待第一个执行步骤。</p>}
      </div>
    </section>
  );
}

function ContextFact({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className={`context-fact ${good ? "good" : ""}`}>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function ContextEmpty({ icon, text }: { icon: React.ReactNode; text: string }) {
  return <div className="context-empty">{icon}<p>{text}</p></div>;
}

function verificationLabel(status: string) {
  if (status === "verified") return "已核验";
  if (status === "hallucinated") return "疑似幻觉";
  if (status === "partial") return "部分匹配";
  if (status === "suspicious") return "需要复核";
  return "待核验";
}

function decisionLabel(decision: Paper["human_decision"]) {
  if (decision === "accepted") return "已接受";
  if (decision === "rejected") return "已拒绝";
  return "待决定";
}

function paperRoleLabel(role: string) {
  if (role === "method_model") return "方法 / 模型论文";
  if (role === "dataset_benchmark") return "数据集 / 基准论文";
  if (role === "survey") return "综述论文";
  if (role === "application") return "应用论文";
  return role;
}

function statusLabel(status: string, controlAction?: string) {
  if (status === "running" && controlAction === "pause") return "正在安全暂停";
  if (status === "running") return "研究进行中";
  if (status === "completed") return "研究已完成";
  if (status === "paused") return "等待人工确认";
  if (status === "failed") return "执行遇到问题";
  if (status === "abandoned") return "研究已废除";
  return "研究准备中";
}

function stageLabel(stage: string) {
  const labels: Record<string, string> = {
    intent_router: "意图识别",
    planner: "任务规划",
    literature_search: "文献检索",
    citation_verification: "引用核验",
    evidence_ledger: "证据入账",
    literature_mining: "文献挖掘",
    paper_classification: "论文分类",
    scientific_data_profile: "数据画像",
    arena: "假设竞技",
    novelty_check: "新颖性检查",
    baseline_quality_gate: "Baseline 质量门",
    experiment_design: "实验设计",
    code_experiment: "代码实验",
    experiment_redesign: "实验重设计",
    report_writer: "报告生成",
    completed: "全部完成",
  };
  return labels[stage] || stage || "等待启动";
}
