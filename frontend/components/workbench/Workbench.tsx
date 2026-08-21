"use client";

import { useEffect, useState } from "react";
import { Beaker, Waves } from "lucide-react";
import {
  BaselineResultCard,
  BrowserCaptureResult,
  PaperPreviewResult,
  RunStepAction,
  actOnRunStep,
  captureBrowserPage,
  continueRun,
  createRun,
  DatasetProfile,
  decideEvidence,
  decidePaper,
  discoverBaselines,
  freezeEvidence,
  freezePapers,
  getDataProfiles,
  getPublicConfig,
  getRun,
  ingestPdfEvidence,
  listRestorableWorkspaces,
  listRuns,
  PublicConfig,
  rebuildReport,
  recoverRun,
  ResearchRun,
  RestorableWorkspace,
  restoreWorkspace,
  runBaseline,
  selectHypothesis,
  startRun,
  previewPaper,
  attachBaselineIntake,
  attachExperimentAssistance,
  BaselineIntakeRequest,
  ExperimentAssistanceInput,
  unfreezeEvidence,
  unfreezePapers,
  verifyBaselineRepo
} from "../../lib/api";
import { abandonRun, pauseRun, resumeRun } from "../../lib/api";
import { BaselineBoard } from "./BaselineBoard";
import { BrowserCapturePanel } from "./BrowserCapturePanel";
import { ClaimAuditPanel } from "./ClaimAuditPanel";
import { CitationVerifier } from "./CitationVerifier";
import { CodeDebugPanel } from "./CodeDebugPanel";
import { CodePlanPanel } from "./CodePlanPanel";
import { EvidenceBoard } from "./EvidenceBoard";
import { ExperimentPlanPanel } from "./ExperimentPlanPanel";
import { ExperimentResultsPanel } from "./ExperimentResultsPanel";
import { FeedbackLoopPanel } from "./FeedbackLoopPanel";
import { HypothesisArena } from "./HypothesisArena";
import { HypothesisArenaPanel } from "./HypothesisArenaPanel";
import { KnowledgeCardsPanel } from "./KnowledgeCardsPanel";
import { LiteratureBoard } from "./LiteratureBoard";
import { PerspectivePlanPanel } from "./PerspectivePlanPanel";
import { ReportViewer } from "./ReportViewer";
import { ResearchConsole, ResearchMode, WorkbenchVersion } from "./ResearchConsole";
import { ResearchConversation } from "./ResearchConversation";
import { ResearchStageContent } from "./ResearchStageContent";
import { ResearchStageNavigator } from "./ResearchStageNavigator";
import { ReviewChecklistPanel } from "./ReviewChecklistPanel";
import { RunHistory } from "./RunHistory";
import { ScientificDataPanel } from "./ScientificDataPanel";
import { SeismicOverviewPanel } from "./SeismicOverviewPanel";
import { StatusStrip } from "./StatusStrip";
import { WorkspacePanel } from "./WorkspacePanel";
import { BaselineIntakePanel } from "./BaselineIntakePanel";
import { ExperimentAssistancePanel } from "./ExperimentAssistancePanel";
import { ResultAnalysisPanel } from "./ResultAnalysisPanel";
import { WorkbenchStageId } from "../../lib/workbench";
import { CompetitionReadinessPanel } from "./CompetitionReadinessPanel";
import { ContextInspector, ContextTab } from "./ContextInspector";

type ConsoleDraft = {
  question: string;
  domain: string;
  researchMode: ResearchMode;
  maxPapers: number;
  workflowMode: "auto" | "guided";
  enableSemanticScholar: boolean;
  enableArxiv: boolean;
  baselineIntake: BaselineIntakeRequest;
  experimentAssistance: ExperimentAssistanceInput;
};

const defaultAssistance: ExperimentAssistanceInput = { objective:"比较已有实验结果", method_summary:"描述已有方法",
  dataset_description:"", baseline_name:"baseline", baseline_metrics:[{name:"accuracy",value:0}],
  method_metrics:[{name:"accuracy",value:0}], ablations:[], logs:[], author_notes:"", source_code:"" };

const classicDefaultQuestion =
  "围绕固态电解质材料的离子电导率与稳定性提升，基于真实文献和开放数据生成可验证科学假设与研究计划。";

const seismicDefaultQuestion =
  "研究地震事件分类中的可验证深度学习改进路径。这里的地震事件分类泛指基于地震波形或时频特征区分不同事件类型的任务，标签可包括自然地震、爆破、诱发或塌陷类事件、噪声/非事件等，但不限于固定四分类。请优先检索地震事件识别、地震波形分类、震相拾取分类、地震/爆破判别等相关深度学习方法与可复现实验基线。";

const defaultDrafts: Record<WorkbenchVersion, ConsoleDraft> = {
  classic: {
    question: classicDefaultQuestion,
    domain: "energy_materials",
    researchMode: "discovery",
    maxPapers: 6,
    workflowMode: "auto",
    enableSemanticScholar: false,
    enableArxiv: true,
    baselineIntake: { strategy: "none" },
    experimentAssistance: {...defaultAssistance}
  },
  seismic: {
    question: seismicDefaultQuestion,
    domain: "seismic_event_classification",
    researchMode: "discovery",
    maxPapers: 6,
    workflowMode: "auto",
    enableSemanticScholar: false,
    enableArxiv: true,
    baselineIntake: { strategy: "ai_generated" },
    experimentAssistance: {...defaultAssistance}
  }
};

function versionForRun(run: Pick<ResearchRun, "domain">): WorkbenchVersion {
  return run.domain === "seismic_event_classification" ? "seismic" : "classic";
}

function statusLabel(status: string, controlAction?: string) {
  if (status === "running" && controlAction === "pause") return "正在暂停";
  if (status === "running") return "运行中";
  if (status === "created") return "已创建";
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  if (status === "paused") return "暂停待审";
  if (status === "abandoned") return "已废除";
  return status;
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
    extract_code_urls: "代码链接提取",
    baseline_discover: "Baseline 发现",
    baseline_verify: "Baseline 验证",
    baseline_quality_gate: "Baseline 质量门",
    re_search_literature: "补充检索",
    experiment_design: "实验设计",
    code_experiment: "写代码并运行",
    macro_react: "宏观修复判断",
    report_writer: "报告生成",
    completed: "完成",
  };
  return labels[stage] || stage || "等待启动";
}

export function Workbench() {
  const [activeVersion, setActiveVersion] = useState<WorkbenchVersion>("classic");
  const [drafts, setDrafts] = useState<Record<WorkbenchVersion, ConsoleDraft>>(defaultDrafts);
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [workspaces, setWorkspaces] = useState<RestorableWorkspace[]>([]);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [profiles, setProfiles] = useState<DatasetProfile[]>([]);
  const [baseline, setBaseline] = useState<BaselineResultCard | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [captureUrl, setCaptureUrl] = useState("https://arxiv.org");
  const [captureBusy, setCaptureBusy] = useState(false);
  const [captureError, setCaptureError] = useState("");
  const [captureResult, setCaptureResult] = useState<BrowserCaptureResult | null>(null);
  const [evidenceBusy, setEvidenceBusy] = useState(false);
  const [citationBusy, setCitationBusy] = useState(false);
  const [hypothesisBusy, setHypothesisBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [baselineBusy, setBaselineBusy] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [controllingRunId, setControllingRunId] = useState<string | null>(null);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<WorkbenchStageId>("plan");
  const [paperPreview, setPaperPreview] = useState<PaperPreviewResult | null>(null);
  const [paperPreviewBusy, setPaperPreviewBusy] = useState(false);
  const [paperPreviewError, setPaperPreviewError] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [mobilePane, setMobilePane] = useState<"conversation" | "workflow" | "paper">("workflow");
  const [contextTab, setContextTab] = useState<ContextTab>("paper");
  const draft = drafts[activeVersion];
  const selectedPaper = run?.papers.find((paper) => paper.paper_id === selectedPaperId) || run?.papers[0] || null;

  useEffect(() => {
    void loadInitialData();
  }, []);

  useEffect(() => {
    if (!run || !["running", "created"].includes(run.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getRun(run.run_id);
        setRun(next);
        await refreshRuns();
      } catch {
        window.clearInterval(timer);
      }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [run?.run_id, run?.status]);

  useEffect(() => {
    setPaperPreview(null);
    setPaperPreviewError("");
    setPaperPreviewBusy(false);
  }, [selectedPaper?.paper_id]);

  async function loadInitialData() {
    const [nextConfig, nextProfiles, nextBaseline, nextRuns, nextWorkspaces] = await Promise.all([
      getPublicConfig().catch(() => null),
      getDataProfiles().catch(() => []),
      runBaseline().catch(() => null),
      listRuns().catch(() => []),
      listRestorableWorkspaces().catch(() => [])
    ]);
    setConfig(nextConfig);
    setProfiles(nextProfiles);
    setBaseline(nextBaseline);
    setRuns(nextRuns);
    setWorkspaces(nextWorkspaces);
  }

  async function refreshRuns() {
    const nextRuns = await listRuns();
    setRuns(nextRuns);
    setWorkspaces(await listRestorableWorkspaces().catch(() => []));
    return nextRuns;
  }

  function updateDraft<K extends keyof ConsoleDraft>(key: K, value: ConsoleDraft[K]) {
    setDrafts((current) => ({
      ...current,
      [activeVersion]: {
        ...current[activeVersion],
        [key]: value
      }
    }));
  }

  function handleVersionChange(nextVersion: WorkbenchVersion) {
    setActiveVersion(nextVersion);
    setError("");
    setRun(null);
    setSelectedPaperId(null);
    setActiveStage("plan");
  }

  function handleSelectRun(nextRun: ResearchRun) {
    setActiveVersion(versionForRun(nextRun));
    setRun(nextRun);
    setSelectedPaperId(nextRun.papers[0]?.paper_id || null);
    setActiveStage(stageForCurrentRun(nextRun));
  }

  async function handleRestoreWorkspace(runId: string, resumeAfterRestore = false) {
    setRestoring(true);
    setError("");
    try {
      const restored = await restoreWorkspace(runId);
      const next = resumeAfterRestore ? await resumeRun(restored.run_id) : restored;
      setActiveVersion(versionForRun(next));
      setRun(next);
      setSelectedPaperId(next.papers[0]?.paper_id || null);
      setActiveStage(stageForCurrentRun(next));
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "工作区恢复失败");
    } finally {
      setRestoring(false);
    }
  }

  async function handlePauseRun(runId: string) {
    setControllingRunId(runId);
    setError("");
    try {
      const next = await pauseRun(runId);
      if (run?.run_id === runId) setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "暂停任务失败");
    } finally {
      setControllingRunId(null);
    }
  }

  async function handleResumeRun(runId: string) {
    setControllingRunId(runId);
    setError("");
    try {
      const next = await resumeRun(runId);
      setActiveVersion(versionForRun(next));
      setRun(next);
      setActiveStage(stageForCurrentRun(next));
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "继续任务失败");
    } finally {
      setControllingRunId(null);
    }
  }

  async function handleAbandonRun(runId: string) {
    const target = runs.find((item) => item.run_id === runId);
    if (!window.confirm(`确认废除“${target?.display_name || target?.question || "该研究任务"}”？已有结果会保留，但任务不能继续运行。`)) return;
    setControllingRunId(runId);
    setError("");
    try {
      const next = await abandonRun(runId);
      if (run?.run_id === runId) setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "废除任务失败");
    } finally {
      setControllingRunId(null);
    }
  }

  async function handleRecoverRun(runId: string) {
    setRestoring(true);
    setError("");
    try {
      const recovered = await recoverRun(runId);
      setActiveVersion(versionForRun(recovered));
      setRun(recovered);
      setActiveStage(stageForCurrentRun(recovered));
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务恢复失败");
    } finally {
      setRestoring(false);
    }
  }

  async function handleStepAction(stepName: string, action: RunStepAction) {
    if (!run) return;
    setActionBusy(true);
    setError("");
    try {
      const next = await actOnRunStep(run.run_id, stepName, action);
      setRun(next);
      setActiveStage(stageForCurrentRun(next));
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "步骤处理失败");
    } finally {
      setActionBusy(false);
    }
  }

  async function retryPaperPreview() {
    if (!selectedPaper?.source_url) return;
    setPaperPreviewBusy(true);
    setPaperPreviewError("");
    try {
      setPaperPreview(await previewPaper(selectedPaper.paper_id, selectedPaper.source_url));
    } catch (err) {
      setPaperPreviewError(err instanceof Error ? err.message : "论文网页抓取失败");
    } finally {
      setPaperPreviewBusy(false);
    }
  }

  async function handleStart() {
    setBusy(true);
    setError("");
    try {
      const runDomain = activeVersion === "seismic" ? "seismic_event_classification" : draft.domain;
      const created = await createRun(
        draft.question,
        runDomain,
        draft.maxPapers,
        draft.enableSemanticScholar,
        draft.enableArxiv,
        draft.workflowMode,
        draft.researchMode
      );
      const withBaseline = runDomain === "seismic_event_classification"
        ? await attachBaselineIntake(created.run_id, draft.baselineIntake) : created;
      const ready = draft.researchMode === "experiment_assistance"
        ? await attachExperimentAssistance(withBaseline.run_id, draft.experimentAssistance) : withBaseline;
      setRun(ready);
      const started = await startRun(ready.run_id);
      setRun(started);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "启动失败");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCurrentRun() {
    if (!run) return;
      const next = await getRun(run.run_id);
      setRun(next);
      setSelectedPaperId((current) => current || next.papers[0]?.paper_id || null);
      await refreshRuns();
  }

  async function handleCapture() {
    setCaptureBusy(true);
    setCaptureError("");
    try {
      setCaptureResult(await captureBrowserPage(captureUrl));
    } catch (err) {
      setCaptureError(err instanceof Error ? err.message : "浏览器抓取失败");
    } finally {
      setCaptureBusy(false);
    }
  }

  async function handleIngestPdf(path: string) {
    if (!run) return;
    setCaptureBusy(true);
    setCaptureError("");
    try {
      const next = await ingestPdfEvidence(run.run_id, path);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setCaptureError(err instanceof Error ? err.message : "PDF 证据导入失败");
    } finally {
      setCaptureBusy(false);
    }
  }

  async function handleEvidenceDecision(evidenceId: string, decision: "pending" | "accepted" | "rejected") {
    if (!run) return;
    setEvidenceBusy(true);
    setError("");
    try {
      const next = await decideEvidence(run.run_id, evidenceId, decision);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "证据决策失败");
    } finally {
      setEvidenceBusy(false);
    }
  }

  async function handleFreezeEvidence() {
    if (!run) return;
    setEvidenceBusy(true);
    setError("");
    try {
      const next = await freezeEvidence(run.run_id);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "证据冻结失败");
    } finally {
      setEvidenceBusy(false);
    }
  }

  async function handleUnfreezeEvidence() {
    if (!run) return;
    setEvidenceBusy(true);
    setError("");
    try {
      const next = await unfreezeEvidence(run.run_id);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "证据解冻失败");
    } finally {
      setEvidenceBusy(false);
    }
  }

  async function handleCitationDecision(paperId: string, decision: "pending" | "accepted" | "rejected") {
    if (!run) return;
    setCitationBusy(true);
    setError("");
    try {
      const next = await decidePaper(run.run_id, paperId, decision);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "引用决策失败");
    } finally {
      setCitationBusy(false);
    }
  }

  async function handleFreezeCitations() {
    if (!run) return;
    setCitationBusy(true);
    setError("");
    try {
      const next = await freezePapers(run.run_id);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "引用冻结失败");
    } finally {
      setCitationBusy(false);
    }
  }

  async function handleUnfreezeCitations() {
    if (!run) return;
    setCitationBusy(true);
    setError("");
    try {
      const next = await unfreezePapers(run.run_id);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "引用解冻失败");
    } finally {
      setCitationBusy(false);
    }
  }

  async function handleSelectHypothesis(hypothesisId: string) {
    if (!run) return;
    setHypothesisBusy(true);
    setError("");
    try {
      const next = await selectHypothesis(run.run_id, hypothesisId);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "假设选择失败");
    } finally {
      setHypothesisBusy(false);
    }
  }

  async function handleRebuildReport() {
    if (!run) return;
    setReportBusy(true);
    setError("");
    try {
      const next = await rebuildReport(run.run_id);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "报告重建失败");
    } finally {
      setReportBusy(false);
    }
  }

  async function handleDiscoverBaselines() {
    if (!run) return;
    setBaselineBusy(true);
    setError("");
    try {
      const next = await discoverBaselines(run.run_id);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Baseline 发现失败");
    } finally {
      setBaselineBusy(false);
    }
  }

  async function handleVerifyBaseline(baselineId: string) {
    if (!run) return;
    setBaselineBusy(true);
    setError("");
    try {
      const next = await verifyBaselineRepo(run.run_id, baselineId);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "仓库验证失败");
    } finally {
      setBaselineBusy(false);
    }
  }

  async function handleContinueRun() {
    if (!run) return;
    setReportBusy(true);
    setError("");
    try {
      const next = await continueRun(run.run_id);
      setRun(next);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "继续运行失败");
    } finally {
      setReportBusy(false);
    }
  }

  return (
    <>
      <div className="mobile-pane-tabs" aria-label="移动端工作区切换">
        {(["conversation", "workflow", "paper"] as const).map((pane) => (
          <button className={mobilePane === pane ? "active" : ""} key={pane} onClick={() => setMobilePane(pane)} type="button">
            {pane === "conversation" ? "任务" : pane === "workflow" ? "流程" : "上下文"}
          </button>
        ))}
      </div>
      <main className="research-workbench">
        <aside className={`conversation-pane ${mobilePane === "conversation" ? "mobile-active" : ""}`}>
          <div className="workbench-brand-row">
            <div className="brand">
              <div className="brand-mark"><Beaker size={19} /></div>
              <span>TrustSci Agent</span>
            </div>
            <div className="version-switch" aria-label="工作区版本">
              <button className={activeVersion === "classic" ? "active" : ""} onClick={() => handleVersionChange("classic")} type="button"><Beaker size={14} />经典</button>
              <button className={activeVersion === "seismic" ? "active" : ""} onClick={() => handleVersionChange("seismic")} type="button"><Waves size={14} />地震</button>
            </div>
          </div>
          <ResearchConsole
            activeVersion={activeVersion}
            question={draft.question}
            domain={draft.domain}
            researchMode={draft.researchMode}
            maxPapers={draft.maxPapers}
            workflowMode={draft.workflowMode}
            enableSemanticScholar={draft.enableSemanticScholar}
            enableArxiv={draft.enableArxiv}
            semanticScholarConfigured={Boolean(config?.semantic_scholar_configured)}
            busy={busy}
            error={error}
            canRefresh={Boolean(run)}
            onQuestionChange={(value) => updateDraft("question", value)}
            onDomainChange={(value) => updateDraft("domain", value)}
            onResearchModeChange={(value) => updateDraft("researchMode", value)}
            onMaxPapersChange={(value) => updateDraft("maxPapers", value)}
            onWorkflowModeChange={(value) => updateDraft("workflowMode", value)}
            onEnableSemanticScholarChange={(value) => updateDraft("enableSemanticScholar", value)}
            onEnableArxivChange={(value) => updateDraft("enableArxiv", value)}
            onStart={handleStart}
            onRefresh={refreshCurrentRun}
          />
          <ResearchConversation run={run} busy={actionBusy} onStepAction={handleStepAction} />
          <RunHistory
            runs={runs}
            workspaces={workspaces}
            selectedRunId={run?.run_id}
            restoring={restoring}
            controllingRunId={controllingRunId}
            onSelect={handleSelectRun}
            onRestore={handleRestoreWorkspace}
            onRecover={handleRecoverRun}
            onPause={handlePauseRun}
            onResume={handleResumeRun}
            onAbandon={handleAbandonRun}
          />
        </aside>

        <section className={`workflow-pane ${mobilePane === "workflow" ? "mobile-active" : ""}`}>
          <div className="topbar">
            <div className="title-block">
              <h1>{activeVersion === "seismic" ? "地震科研专家" : "可信 AI Scientist 工作台"}</h1>
              <p>{run?.question || "从左侧输入研究任务，系统将直接开始执行。"}</p>
            </div>
            <div className="topbar-badges">
              <span className="badge">{activeVersion === "seismic" ? "地震任务" : "经典流程"}</span>
              <span className="badge">{run ? `${statusLabel(run.status, run.control_action)} / ${stageLabel(run.current_stage)}` : "等待启动"}</span>
            </div>
          </div>
          <StatusStrip config={config} run={run} />
          <CompetitionReadinessPanel config={config} run={run} />
          <ResearchStageNavigator run={run} activeStage={activeStage} onSelect={(stage) => { setActiveStage(stage); setMobilePane("workflow"); }} />
          <ResearchStageContent
            activeStage={activeStage}
            sections={{
              plan: <div className="grid"><PerspectivePlanPanel run={run} /></div>,
              literature: (
                <div className="grid">
                  <LiteratureBoard run={run} selectedPaperId={selectedPaper?.paper_id || null} onSelectPaper={(paperId) => { setSelectedPaperId(paperId); setContextTab("paper"); setMobilePane("paper"); }} />
                  <CitationVerifier run={run} busy={citationBusy} onDecision={handleCitationDecision} onFreeze={handleFreezeCitations} onUnfreeze={handleUnfreezeCitations} />
                  <EvidenceBoard run={run} busy={evidenceBusy} onDecision={handleEvidenceDecision} onFreeze={handleFreezeEvidence} onUnfreeze={handleUnfreezeEvidence} />
                  <KnowledgeCardsPanel run={run} />
                  {activeVersion === "classic" && <BrowserCapturePanel url={captureUrl} result={captureResult} busy={captureBusy} error={captureError} canIngestPdf={Boolean(run)} onUrlChange={setCaptureUrl} onCapture={handleCapture} onIngestPdf={handleIngestPdf} />}
                </div>
              ),
              hypothesis: (
                <div className="grid">
                  {activeVersion === "seismic" ? <><SeismicOverviewPanel run={run} /><HypothesisArenaPanel run={run} /></> : <><ScientificDataPanel run={run} profiles={profiles} baseline={baseline} /><HypothesisArena run={run} busy={hypothesisBusy} onSelect={handleSelectHypothesis} /></>}
                </div>
              ),
              baseline: (
                <div className="grid">
                  {activeVersion === "seismic" ? <><BaselineIntakePanel value={draft.baselineIntake} onChange={(value) => updateDraft("baselineIntake", value)} /><BaselineBoard run={run} busy={baselineBusy} onDiscover={handleDiscoverBaselines} onVerify={handleVerifyBaseline} /></> : <ScientificDataPanel run={run} profiles={profiles} baseline={baseline} />}
                </div>
              ),
              experiment: (
                <div className="grid">
                  {activeVersion === "seismic" && draft.researchMode === "experiment_assistance" && <ExperimentAssistancePanel value={draft.experimentAssistance} onChange={(value) => updateDraft("experimentAssistance", value)} />}
                  <ExperimentPlanPanel run={run} />
                  {run?.code_experiment && <><CodePlanPanel ce={run.code_experiment} /><CodeDebugPanel ce={run.code_experiment} /><ExperimentResultsPanel ce={run.code_experiment} /></>}
                  {run && <FeedbackLoopPanel run={run} />}
                  <ResultAnalysisPanel run={run} />
                </div>
              ),
              report: (
                <div className="grid">
                  <ReviewChecklistPanel run={run} busy={reportBusy} onContinueRun={handleContinueRun} onRebuildReport={handleRebuildReport} />
                  <ClaimAuditPanel run={run} />
                  <ReportViewer run={run} config={config} />
                  <WorkspacePanel run={run} />
                </div>
              ),
            }}
          />
        </section>

        <aside className={`paper-pane context-pane ${mobilePane === "paper" ? "mobile-active" : ""}`}>
          <ContextInspector
            activeTab={contextTab}
            run={run}
            paper={selectedPaper}
            preview={paperPreview}
            loading={paperPreviewBusy}
            error={paperPreviewError}
            onTabChange={setContextTab}
            onRetryPreview={retryPaperPreview}
          />
        </aside>
      </main>
    </>
  );
}

function stageForCurrentRun(run: ResearchRun): WorkbenchStageId {
  const stage = run.current_stage;
  if (["intent_router", "planner", "created", "queued"].includes(stage)) return "plan";
  if (["literature_search", "citation_verification", "evidence_ledger", "literature_mining", "paper_classification", "awaiting_citation_review", "awaiting_evidence_review"].includes(stage)) return "literature";
  if (["scientific_data_profile", "hypothesis_debate", "arena", "novelty_check"].includes(stage)) return "hypothesis";
  if (["baseline_intake", "baseline_quality_gate"].includes(stage)) return "baseline";
  if (["experiment_design", "code_experiment", "experiment_result_gate", "experiment_redesign", "result_evaluation", "ablation_analysis", "result_interpretation"].includes(stage)) return "experiment";
  return "report";
}
