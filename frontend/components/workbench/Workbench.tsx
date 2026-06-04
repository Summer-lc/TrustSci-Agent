"use client";

import { useEffect, useState } from "react";
import { Beaker } from "lucide-react";
import {
  BaselineResultCard,
  BrowserCaptureResult,
  captureBrowserPage,
  createRun,
  DatasetProfile,
  getDataProfiles,
  getPublicConfig,
  getRun,
  ingestPdfEvidence,
  listRuns,
  PublicConfig,
  ResearchRun,
  runBaseline,
  startRun
} from "../../lib/api";
import { BrowserCapturePanel } from "./BrowserCapturePanel";
import { CitationVerifier } from "./CitationVerifier";
import { EvidenceBoard } from "./EvidenceBoard";
import { ExperimentPlanPanel } from "./ExperimentPlanPanel";
import { HypothesisArena } from "./HypothesisArena";
import { ReportViewer } from "./ReportViewer";
import { ResearchConsole } from "./ResearchConsole";
import { RunHistory } from "./RunHistory";
import { RunTimeline } from "./RunTimeline";
import { ScientificDataPanel } from "./ScientificDataPanel";
import { StatusStrip } from "./StatusStrip";

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
          <EvidenceBoard run={run} />
          <CitationVerifier run={run} />
          <ScientificDataPanel run={run} profiles={profiles} baseline={baseline} />
          <HypothesisArena run={run} />
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
