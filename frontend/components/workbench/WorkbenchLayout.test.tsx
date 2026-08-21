import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BaselineBoard } from "./BaselineBoard";
import { BaselineIntakePanel } from "./BaselineIntakePanel";
import { CompetitionReadinessPanel } from "./CompetitionReadinessPanel";
import { ContextInspector } from "./ContextInspector";
import { LiteratureBoard } from "./LiteratureBoard";
import { ResearchConsole } from "./ResearchConsole";
import { RunHistory } from "./RunHistory";
import { ResearchStageNavigator } from "./ResearchStageNavigator";
import { PerspectivePlanPanel } from "./PerspectivePlanPanel";
import { ResearchRun } from "../../lib/api";

const noop = () => undefined;

const paperRun = {
  domain: "seismic_event_classification",
  papers: [{
    paper_id: "paper-1",
    title: "A transparent benchmark for seismic event classification",
    authors: ["Lin", "Chen"],
    year: 2025,
    venue: "Scientific Data",
    source_api: "OpenAlex",
    abstract: "A benchmark with reproducible evaluation.",
    fields_of_study: ["Seismology"],
    is_retracted: false,
    verification_status: "verified",
    report_eligible: true,
    human_decision: "accepted",
    human_note: "",
    frozen: true,
    paper_role: "dataset_benchmark",
    seismic_relevant: true,
    baseline_eligible: true,
  }],
  steps: [
    { name: "citation_verification", status: "completed", summary: "引用已核验" },
    { name: "paper_classification", status: "completed", summary: "论文已分类" },
  ],
} as unknown as ResearchRun;

describe("workbench progressive disclosure", () => {
  it("renders readiness as a collapsible summary", () => {
    const html = renderToStaticMarkup(<CompetitionReadinessPanel run={null} config={null} />);

    expect(html).toContain("<details");
    expect(html).toContain("<summary");
    expect(html).not.toMatch(/参赛|竞赛|COMPETITION/);
  });

  it("shows explanatory copy only for the active stage", () => {
    const html = renderToStaticMarkup(
      <ResearchStageNavigator run={null} activeStage="plan" onSelect={() => undefined} />,
    );

    expect(html).toContain("识别研究模式并生成检索计划");
    expect(html.match(/<small>/g)).toHaveLength(1);
  });

  it("gives both Baseline cards the full workflow width", () => {
    const intake = renderToStaticMarkup(
      <BaselineIntakePanel value={{ strategy: "ai_generated" }} onChange={() => undefined} />,
    );
    const board = renderToStaticMarkup(
      <BaselineBoard run={null} busy={false} onDiscover={() => undefined} onVerify={() => undefined} />,
    );

    expect(intake).toContain('class="panel span-12 baseline-intake-panel"');
    expect(board).toContain('class="panel span-12 baseline-board"');
  });

  it("uses the full workflow width for a standalone stage panel", () => {
    const html = renderToStaticMarkup(<PerspectivePlanPanel run={null} />);

    expect(html).toContain('class="panel span-12"');
  });

  it("keeps advanced research controls inside a collapsed settings section", () => {
    const html = renderToStaticMarkup(
      <ResearchConsole
        activeVersion="seismic"
        question="如何提高地震事件分类的可信度？"
        domain="seismic_event_classification"
        researchMode="discovery"
        maxPapers={6}
        workflowMode="auto"
        enableSemanticScholar={false}
        enableArxiv
        semanticScholarConfigured={false}
        busy={false}
        error=""
        canRefresh={false}
        onQuestionChange={noop}
        onDomainChange={noop}
        onResearchModeChange={noop}
        onMaxPapersChange={noop}
        onWorkflowModeChange={noop}
        onEnableSemanticScholarChange={noop}
        onEnableArxivChange={noop}
        onStart={noop}
        onRefresh={noop}
      />,
    );

    expect(html).toContain('class="research-settings"');
    expect(html).toContain("<summary");
    expect(html).toContain("研究设置");
    expect(html).toContain("启动研究");
  });

  it("provides paper, evidence and run context tabs", () => {
    const html = renderToStaticMarkup(
      <ContextInspector
        activeTab="paper"
        run={paperRun}
        paper={paperRun.papers[0]}
        preview={null}
        loading={false}
        error=""
        onTabChange={noop}
        onRetryPreview={noop}
      />,
    );

    expect(html).toContain('aria-label="科研上下文"');
    expect(html).toContain("文献");
    expect(html).toContain("证据");
    expect(html).toContain("运行");
  });

  it("renders literature candidates as a selectable evidence matrix", () => {
    const html = renderToStaticMarkup(
      <LiteratureBoard run={paperRun} selectedPaperId="paper-1" onSelectPaper={noop} />,
    );

    expect(html).toContain('class="evidence-table"');
    expect(html).toContain('class="evidence-row active"');
    expect(html).toContain("来源 / 年份");
    expect(html).toContain("可进报告");
  });

  it("shows a concrete run name with pause and abandon actions", () => {
    const run = {
      run_id: "run_a1b2c3d4",
      display_name: "真实波形地震事件分类研究",
      question: "真实波形地震事件分类研究",
      status: "running",
      control_action: "none",
      pause_reason: null,
      current_stage: "literature_search",
      updated_at: "2026-08-10T08:00:00Z",
    } as unknown as ResearchRun;
    const props = {
      runs: [run], workspaces: [], selectedRunId: run.run_id, restoring: false, controllingRunId: null,
      onSelect: noop, onRestore: noop, onRecover: noop, onPause: noop, onResume: noop, onAbandon: noop,
    } as any;

    const html = renderToStaticMarkup(<RunHistory {...props} />);

    expect(html).toContain("真实波形地震事件分类研究");
    expect(html).not.toContain("run_a1b2c3d4");
    expect(html).toContain("暂停");
    expect(html).toContain("废除");
  });

  it("offers continue for a user-paused run", () => {
    const run = {
      run_id: "run_paused",
      display_name: "暂停后的可信实验研究",
      question: "暂停后的可信实验研究",
      status: "paused",
      control_action: "none",
      pause_reason: "user",
      current_stage: "experiment_design",
    } as unknown as ResearchRun;
    const props = {
      runs: [run], workspaces: [], selectedRunId: null, restoring: false, controllingRunId: null,
      onSelect: noop, onRestore: noop, onRecover: noop, onPause: noop, onResume: noop, onAbandon: noop,
    } as any;

    const html = renderToStaticMarkup(<RunHistory {...props} />);

    expect(html).toContain("继续运行");
    expect(html).not.toContain("恢复到可处理状态");
  });
});
