import { PublicConfig, ResearchRun, RunStepAction } from "./api";


export type WorkbenchStageId =
  | "plan"
  | "literature"
  | "hypothesis"
  | "baseline"
  | "experiment"
  | "report";

export type ConversationMessage = {
  id: string;
  kind: "user" | "info" | "success" | "warning" | "error";
  title: string;
  text: string;
  stepName?: string;
};

export type ReadinessStatus = "ready" | "warning" | "blocked";

export type CompetitionReadinessCheck = {
  id: "qwen" | "dataset" | "references" | "experiment" | "report";
  label: string;
  status: ReadinessStatus;
  detail: string;
};

export type CompetitionReadiness = {
  state: ReadinessStatus;
  score: number;
  readyCount: number;
  checks: CompetitionReadinessCheck[];
};

export type ReportExportNotice = {
  tone: "warning" | "blocked";
  title: string;
  detail: string;
};

export type PaperReadTarget = {
  kind: "embedded_pdf" | "external_pdf" | "source_only";
  url: string | null;
};

export type RunLifecycleAction = "pause" | "resume" | "review" | "recover" | "abandon";

type RunHistoryState = {
  status: string;
  control_action?: "none" | "pause" | "abandon" | null;
  pause_reason?: "user" | "review" | "error" | null;
};

export function runDisplayName(run: { display_name?: string | null; question?: string | null }) {
  const explicit = run.display_name?.trim();
  if (explicit) return explicit;
  const normalized = (run.question || "").trim().replace(/\s+/g, " ") || "未命名研究任务";
  return normalized.length <= 32 ? normalized : `${normalized.slice(0, 31)}…`;
}

export function runHistoryActions(run: RunHistoryState): RunLifecycleAction[] {
  if (run.status === "running") {
    return run.control_action === "pause" ? ["abandon"] : ["pause", "abandon"];
  }
  if (run.status === "paused") {
    if (run.pause_reason === "user") return ["resume", "abandon"];
    if (run.pause_reason === "review") return ["review", "abandon"];
    return ["recover", "abandon"];
  }
  if (run.status === "failed") return ["recover", "abandon"];
  if (run.status === "created") return ["abandon"];
  return [];
}

type PaperReadSource = {
  pdf_url?: string | null;
  source_url?: string | null;
  arxiv_id?: string | null;
};

const DEMO_DATA_PATTERN = /(demo|synthetic|sample|bundled|harness|模拟|合成|演示)/i;

export function buildCompetitionReadiness(
  run: ResearchRun | null,
  config: Pick<PublicConfig, "llm_enabled" | "qwen_model"> | null,
): CompetitionReadiness {
  const checks: CompetitionReadinessCheck[] = [
    qwenReadiness(config),
    datasetReadiness(run),
    referenceReadiness(run),
    experimentReadiness(run),
    reportReadiness(run),
  ];
  const readyCount = checks.filter((check) => check.status === "ready").length;
  const warningCount = checks.filter((check) => check.status === "warning").length;
  const state: ReadinessStatus = checks.some((check) => check.status === "blocked")
    ? "blocked"
    : warningCount > 0
      ? "warning"
      : "ready";

  return {
    state,
    readyCount,
    score: readyCount * 20 + warningCount * 10,
    checks,
  };
}

export function reportExportNotice(readiness: CompetitionReadiness): ReportExportNotice | null {
  if (readiness.state === "ready") return null;
  if (readiness.state === "warning") {
    return {
      tone: "warning",
      title: "导出前仍需人工核验",
      detail: `研究可信度 ${readiness.score}/100；黄色检查项尚未完全确认。`,
    };
  }
  return {
    tone: "blocked",
    title: "当前导出为可信性草稿",
    detail: `研究可信度 ${readiness.score}/100；请先补齐红色检查项。`,
  };
}

export function resolvePaperReadTarget(paper: PaperReadSource | null): PaperReadTarget {
  if (!paper) return { kind: "source_only", url: null };

  const explicitPdf = paper.pdf_url?.trim();
  if (explicitPdf) {
    return {
      kind: isDirectPdfUrl(explicitPdf) ? "embedded_pdf" : "external_pdf",
      url: explicitPdf,
    };
  }

  const arxivId = paper.arxiv_id?.replace(/^arxiv:/i, "").trim();
  if (arxivId && /^[a-z0-9./-]+(?:v\d+)?$/i.test(arxivId)) {
    return { kind: "embedded_pdf", url: `https://arxiv.org/pdf/${arxivId}` };
  }

  const sourceUrl = paper.source_url?.trim() || null;
  if (sourceUrl && isDirectPdfUrl(sourceUrl)) {
    return { kind: "embedded_pdf", url: sourceUrl };
  }
  const sourceArxivId = sourceUrl?.match(/arxiv\.org\/abs\/([^?#]+)/i)?.[1];
  if (sourceArxivId) {
    return { kind: "embedded_pdf", url: `https://arxiv.org/pdf/${sourceArxivId}` };
  }
  return { kind: "source_only", url: sourceUrl };
}

function isDirectPdfUrl(url: string) {
  return /\.pdf(?:$|[?#])/i.test(url) || /\/arxiv\.org\/pdf\//i.test(url);
}

function qwenReadiness(
  config: Pick<PublicConfig, "llm_enabled" | "qwen_model"> | null,
): CompetitionReadinessCheck {
  return config?.llm_enabled
    ? { id: "qwen", label: "百炼与千问", status: "ready", detail: `${config.qwen_model} 已连接` }
    : { id: "qwen", label: "百炼与千问", status: "blocked", detail: "当前为备用模式，缺少正式调用证据" };
}

function datasetReadiness(run: ResearchRun | null): CompetitionReadinessCheck {
  const profiles = run?.data_profiles || [];
  const seismic = run?.seismic_data_profile;
  if (!profiles.length && !seismic) {
    return { id: "dataset", label: "真实数据", status: "blocked", detail: "尚未生成数据画像" };
  }

  const sources = [
    ...profiles.flatMap((profile) => [profile.name, profile.source, profile.notes, profile.availability]),
    seismic?.dataset_name || "",
    seismic?.source_path || "",
  ].filter(Boolean);
  if (sources.some((source) => DEMO_DATA_PATTERN.test(source))) {
    return { id: "dataset", label: "真实数据", status: "blocked", detail: "检测到演示或合成数据，不能作为正式实证" };
  }

  const label = profiles[0]?.name || seismic?.dataset_name || "科研数据集";
  return { id: "dataset", label: "真实数据", status: "ready", detail: `${label} 已建立数据画像` };
}

function referenceReadiness(run: ResearchRun | null): CompetitionReadinessCheck {
  const eligible = run?.papers.filter((paper) => paper.report_eligible).length || 0;
  if (eligible >= 3) {
    return { id: "references", label: "真实文献", status: "ready", detail: `${eligible} 篇文献可进入报告` };
  }
  if (eligible > 0) {
    return { id: "references", label: "真实文献", status: "warning", detail: `仅 ${eligible} 篇有效文献，证据覆盖偏弱` };
  }
  return { id: "references", label: "真实文献", status: "blocked", detail: "没有可进入报告的核验文献" };
}

function experimentReadiness(run: ResearchRun | null): CompetitionReadinessCheck {
  const experiment = run?.code_experiment;
  const gate = experiment?.acceptance_gate;
  const passed = Boolean(
    gate?.tests_pass &&
    gate.metrics_generated &&
    gate.baseline_comparison_written &&
    experiment?.comparison.outcome !== "failed",
  );
  if (passed) {
    return { id: "experiment", label: "实际实验", status: "ready", detail: "测试、指标和 baseline 对比均已完成" };
  }
  if (run?.experiment_assistance) {
    return { id: "experiment", label: "实际实验", status: "warning", detail: "已导入人工结果，仍需核验来源与复现记录" };
  }
  return { id: "experiment", label: "实际实验", status: "blocked", detail: "尚无通过验收门的实验结果" };
}

function reportReadiness(run: ResearchRun | null): CompetitionReadinessCheck {
  if (!run?.report) {
    return { id: "report", label: "标准报告", status: "blocked", detail: "尚未生成《科学假设与研究计划》" };
  }
  if (!run.claim_audit) {
    return { id: "report", label: "标准报告", status: "warning", detail: "报告已生成，结论支持度尚未核验" };
  }
  if (run.claim_audit.unsupported > 0) {
    return { id: "report", label: "标准报告", status: "warning", detail: `${run.claim_audit.unsupported} 条结论缺少证据支持` };
  }
  return { id: "report", label: "标准报告", status: "ready", detail: "报告已生成，未发现不支持结论" };
}

export const STAGE_GROUPS: Array<{
  id: WorkbenchStageId;
  label: string;
  description: string;
  stepNames: string[];
}> = [
  {
    id: "plan",
    label: "研究目标与计划",
    description: "识别研究模式并生成检索计划",
    stepNames: ["intent_router", "planner"],
  },
  {
    id: "literature",
    label: "文献与证据",
    description: "检索、核验、冻结并提炼证据",
    stepNames: [
      "literature_search",
      "citation_verification",
      "awaiting_citation_review",
      "evidence_ledger",
      "literature_mining",
      "paper_classification",
      "awaiting_evidence_review",
    ],
  },
  {
    id: "hypothesis",
    label: "假设与评审",
    description: "数据画像、假设生成与多智能体评审",
    stepNames: [
      "scientific_data_profile",
      "hypothesis_debate",
      "arena",
      "novelty_check",
    ],
  },
  {
    id: "baseline",
    label: "可信 Baseline",
    description: "人工上传或 AI 生成并完成质量门检查",
    stepNames: ["baseline_intake", "baseline_quality_gate"],
  },
  {
    id: "experiment",
    label: "实验与重设计循环",
    description: "实验设计、代码执行、结果判断与重设计",
    stepNames: [
      "experiment_design",
      "code_experiment",
      "experiment_result_gate",
      "experiment_redesign",
      "result_evaluation",
      "ablation_analysis",
      "result_interpretation",
    ],
  },
  {
    id: "report",
    label: "报告与核验",
    description: "报告生成、声明核验、修订、翻译与导出",
    stepNames: [
      "report_writer",
      "claim_verification",
      "report_revision",
      "claim_reverification",
      "report_translation",
    ],
  },
];

type RunStep = ResearchRun["steps"][number];

export function groupRunStages(steps: RunStep[]) {
  return STAGE_GROUPS.map((group) => ({
    ...group,
    steps: steps.filter((step) => group.stepNames.includes(step.name)),
  }));
}

export function stepActions(
  step: Pick<RunStep, "name" | "status" | "summary" | "retryable" | "skippable">,
): RunStepAction[] {
  if (step.status !== "waiting_action") return [];
  const actions: RunStepAction[] = [];
  if (step.retryable) actions.push("retry");
  if (step.skippable) actions.push("skip");
  return actions;
}

export function buildConversationMessages(
  run: Pick<ResearchRun, "question" | "status" | "steps" | "errors">,
): ConversationMessage[] {
  const messages: ConversationMessage[] = [
    {
      id: "question",
      kind: "user",
      title: "研究任务",
      text: run.question,
    },
  ];
  run.steps.forEach((step, index) => {
    const kind = step.status === "completed"
      ? "success"
      : step.status === "failed" || step.status === "waiting_action"
        ? "error"
        : step.status === "retrying" || step.status === "skipped"
          ? "warning"
          : "info";
    messages.push({
      id: `${step.name}-${index}`,
      kind,
      title: stepLabel(step.name),
      text: step.summary || statusLabel(step.status),
      stepName: step.name,
    });
  });
  run.errors.forEach((error, index) => messages.push({
    id: `run-error-${index}`,
    kind: "error",
    title: "运行错误",
    text: error,
  }));
  if (run.status === "completed") {
    messages.push({
      id: "completed",
      kind: "success",
      title: "研究任务已完成",
      text: "报告、证据记录和实验结果已经生成。",
    });
  }
  return messages;
}

export function stepLabel(name: string) {
  const labels: Record<string, string> = {
    intent_router: "研究意图识别",
    planner: "研究计划",
    literature_search: "文献检索",
    citation_verification: "引用核验",
    evidence_ledger: "证据台账",
    literature_mining: "文献提炼",
    paper_classification: "论文分类",
    scientific_data_profile: "数据画像",
    hypothesis_debate: "假设评审",
    arena: "假设竞技场",
    novelty_check: "创新性检查",
    baseline_intake: "可信 Baseline 接入",
    baseline_quality_gate: "Baseline 质量门",
    experiment_design: "实验设计",
    code_experiment: "代码实验",
    experiment_result_gate: "实验结果判断",
    experiment_redesign: "实验重新设计",
    result_evaluation: "结果评估",
    ablation_analysis: "消融分析",
    result_interpretation: "结果解释",
    report_writer: "报告生成",
    claim_verification: "声明核验",
    report_revision: "报告修订",
    claim_reverification: "声明复核",
    report_translation: "报告翻译",
  };
  return labels[name] || name;
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: "等待执行",
    running: "正在执行",
    retrying: "自动重试中",
    completed: "已完成",
    waiting_action: "等待处理",
    skipped: "已跳过",
    failed: "执行失败",
    paused: "已暂停",
  };
  return labels[status] || status;
}
