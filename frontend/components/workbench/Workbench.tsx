"use client";

import { useEffect, useState } from "react";
import { Beaker } from "lucide-react";
import {
  BaselineResultCard,
  BrowserCaptureResult,
  captureBrowserPage,
  createRun,
  DatasetProfile,
  decidePaper,
  decideEvidence,
  freezeEvidence,
  freezePapers,
  getDataProfiles,
  getPublicConfig,
  getRun,
  ingestPdfEvidence,
  listRuns,
  PublicConfig,
  ResearchRun,
  runBaseline,
  selectHypothesis,
  startRun,
  unfreezeEvidence,
  unfreezePapers
} from "../../lib/api";
import { BrowserCapturePanel } from "./BrowserCapturePanel";
import { ClaimAuditPanel } from "./ClaimAuditPanel";
import { CitationVerifier } from "./CitationVerifier";
import { EvidenceBoard } from "./EvidenceBoard";
import { ExperimentPlanPanel } from "./ExperimentPlanPanel";
import { HypothesisArena } from "./HypothesisArena";
import { KnowledgeCardsPanel } from "./KnowledgeCardsPanel";
import { LiteratureBoard } from "./LiteratureBoard";
import { PerspectivePlanPanel } from "./PerspectivePlanPanel";
import { ReportViewer } from "./ReportViewer";
import { ResearchConsole } from "./ResearchConsole";
import { RunHistory } from "./RunHistory";
import { RunTimeline } from "./RunTimeline";
import { ScientificDataPanel } from "./ScientificDataPanel";
import { StatusStrip } from "./StatusStrip";
import { WorkspacePanel } from "./WorkspacePanel";

const defaultQuestion =
  "请围绕固态电解质材料的离子电导率与稳定性提升，基于真实文献和开放数据库，生成可验证科学假设与实验计划。";

export function Workbench() {
  const [question, setQuestion] = useState(defaultQuestion);
  const [domain, setDomain] = useState("energy_materials");
  const [maxPapers, setMaxPapers] = useState(6);
  const [enableSemanticScholar, setEnableSemanticScholar] = useState(false);
  const [enableArxiv, setEnableArxiv] = useState(true);
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [runs, setRuns] = useState<ResearchRun[]>([]);
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

  async function loadInitialData() {
    const [nextConfig, nextProfiles, nextBaseline, nextRuns] = await Promise.all([
      getPublicConfig().catch(() => null),
      getDataProfiles().catch(() => []),
      runBaseline().catch(() => null),
      listRuns().catch(() => [])
    ]);
    setConfig(nextConfig);
    setProfiles(nextProfiles);
    setBaseline(nextBaseline);
    setRuns(nextRuns);
    if (nextRuns[0]) setRun(nextRuns[0]);
  }

  async function refreshRuns() {
    const nextRuns = await listRuns();
    setRuns(nextRuns);
    return nextRuns;
  }

  async function handleStart() {
    setBusy(true);
    setError("");
    try {
      const created = await createRun(question, domain, maxPapers, enableSemanticScholar, enableArxiv);
      setRun(created);
      const started = await startRun(created.run_id);
      setRun(started);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCurrentRun() {
    if (!run) return;
    const next = await getRun(run.run_id);
    setRun(next);
    await refreshRuns();
  }

  async function handleCapture() {
    setCaptureBusy(true);
    setCaptureError("");
    try {
      setCaptureResult(await captureBrowserPage(captureUrl));
    } catch (err) {
      setCaptureError(err instanceof Error ? err.message : "Browser capture failed");
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
      setCaptureError(err instanceof Error ? err.message : "PDF evidence ingest failed");
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
      setError(err instanceof Error ? err.message : "Evidence decision failed");
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
      setError(err instanceof Error ? err.message : "Evidence freeze failed");
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
      setError(err instanceof Error ? err.message : "Evidence unfreeze failed");
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
      setError(err instanceof Error ? err.message : "Citation decision failed");
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
      setError(err instanceof Error ? err.message : "Citation freeze failed");
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
      setError(err instanceof Error ? err.message : "Citation unfreeze failed");
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
      setError(err instanceof Error ? err.message : "Hypothesis selection failed");
    } finally {
      setHypothesisBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Beaker size={19} /></div>
          <span>TrustSci Agent</span>
        </div>
        <ResearchConsole
          question={question}
          domain={domain}
          maxPapers={maxPapers}
          enableSemanticScholar={enableSemanticScholar}
          enableArxiv={enableArxiv}
          semanticScholarConfigured={Boolean(config?.semantic_scholar_configured)}
          busy={busy}
          error={error}
          canRefresh={Boolean(run)}
          onQuestionChange={setQuestion}
          onDomainChange={setDomain}
          onMaxPapersChange={setMaxPapers}
          onEnableSemanticScholarChange={setEnableSemanticScholar}
          onEnableArxivChange={setEnableArxiv}
          onStart={handleStart}
          onRefresh={refreshCurrentRun}
        />
        <RunHistory runs={runs} selectedRunId={run?.run_id} onSelect={setRun} />
      </aside>

      <section className="content">
        <div className="topbar">
          <div className="title-block">
            <h1>可信多智能体 AI Scientist 工作台</h1>
            <p>{run?.question || question}</p>
          </div>
          <span className="badge">{run ? `${run.status} / ${run.current_stage}` : "idle"}</span>
        </div>

        <StatusStrip config={config} run={run} />

        <div className="grid">
          <RunTimeline run={run} />
          <WorkspacePanel run={run} />
          <PerspectivePlanPanel run={run} />
          <LiteratureBoard run={run} />
          <EvidenceBoard
            run={run}
            busy={evidenceBusy}
            onDecision={handleEvidenceDecision}
            onFreeze={handleFreezeEvidence}
            onUnfreeze={handleUnfreezeEvidence}
          />
          <KnowledgeCardsPanel run={run} />
          <ClaimAuditPanel run={run} />
          <CitationVerifier
            run={run}
            busy={citationBusy}
            onDecision={handleCitationDecision}
            onFreeze={handleFreezeCitations}
            onUnfreeze={handleUnfreezeCitations}
          />
          <ScientificDataPanel run={run} profiles={profiles} baseline={baseline} />
          <HypothesisArena run={run} busy={hypothesisBusy} onSelect={handleSelectHypothesis} />
          <ExperimentPlanPanel run={run} />
          <BrowserCapturePanel
            url={captureUrl}
            result={captureResult}
            busy={captureBusy}
            error={captureError}
            canIngestPdf={Boolean(run)}
            onUrlChange={setCaptureUrl}
            onCapture={handleCapture}
            onIngestPdf={handleIngestPdf}
          />
          <ReportViewer run={run} />
        </div>
      </section>
    </main>
  );
}
