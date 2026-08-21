import { describe, expect, it } from "vitest";

import {
  buildConversationMessages,
  buildCompetitionReadiness,
  groupRunStages,
  reportExportNotice,
  resolvePaperReadTarget,
  runDisplayName,
  runHistoryActions,
  stepActions,
} from "./workbench";
import { PublicConfig, ResearchRun } from "./api";


describe("workbench view models", () => {
  it("shows retry and skip only for a skippable waiting step", () => {
    expect(
      stepActions({
        name: "literature_mining",
        status: "waiting_action",
        summary: "failed",
        retryable: true,
        skippable: true,
      }),
    ).toEqual(["retry", "skip"]);
    expect(
      stepActions({
        name: "report_writer",
        status: "waiting_action",
        summary: "failed",
        retryable: true,
        skippable: false,
      }),
    ).toEqual(["retry"]);
  });

  it("groups experiment redesign into the experiment stage", () => {
    const groups = groupRunStages([
      {
        name: "experiment_redesign",
        status: "completed",
        summary: "round 1",
      },
    ]);

    expect(groups.find((group) => group.id === "experiment")?.steps).toHaveLength(1);
  });

  it("creates a warning message from retry state", () => {
    const messages = buildConversationMessages({
      steps: [
        {
          name: "literature_search",
          status: "retrying",
          summary: "retry",
          attempts: 1,
        },
      ],
      errors: [],
      status: "running",
      question: "test question",
    });

    expect(messages[1].kind).toBe("warning");
    expect(messages[1].text).toContain("retry");
  });

  it("keeps backend order inside a stage", () => {
    const groups = groupRunStages([
      { name: "literature_search", status: "completed", summary: "first" },
      { name: "citation_verification", status: "completed", summary: "second" },
    ]);

    expect(groups.find((group) => group.id === "literature")?.steps.map((step) => step.name)).toEqual([
      "literature_search",
      "citation_verification",
    ]);
  });

  it("blocks submission readiness when no run exists", () => {
    const readiness = buildCompetitionReadiness(null, {
      llm_enabled: false,
      qwen_model: "qwen-plus",
    } as PublicConfig);

    expect(readiness.state).toBe("blocked");
    expect(readiness.readyCount).toBe(0);
    expect(readiness.checks).toHaveLength(5);
    expect(readiness.checks.find((item) => item.id === "qwen")?.status).toBe("blocked");
  });

  it("never presents synthetic demo data as a real dataset", () => {
    const readiness = buildCompetitionReadiness({
      data_profiles: [{
        name: "demo_seismic_events",
        source: "deterministic synthetic waveform harness",
        fields: ["waveform"],
        task_type: "classification",
        availability: "available",
        notes: "demo only",
      }],
      papers: [],
      steps: [],
      errors: [],
      constraints: { workflow_mode: "auto" },
    } as unknown as ResearchRun, { llm_enabled: true, qwen_model: "qwen-plus" } as PublicConfig);

    const dataset = readiness.checks.find((item) => item.id === "dataset");
    expect(dataset?.status).toBe("blocked");
    expect(dataset?.detail).toContain("演示");
    expect(readiness.state).toBe("blocked");
  });

  it("marks a fully evidenced real-data run as ready", () => {
    const papers = [1, 2, 3].map((index) => ({ paper_id: `p${index}`, report_eligible: true }));
    const readiness = buildCompetitionReadiness({
      data_profiles: [{
        name: "STEAD waveform subset",
        source: "Stanford Earthquake Dataset",
        source_url: "https://github.com/smousavi05/STEAD",
        rows: 12000,
        fields: ["waveform", "label"],
        target: "event_type",
        task_type: "classification",
        availability: "available",
        notes: "licensed public scientific dataset",
      }],
      papers,
      code_experiment: {
        acceptance_gate: {
          tests_pass: true,
          metrics_generated: true,
          baseline_comparison_written: true,
        },
        comparison: { outcome: "completed_positive" },
        summary: { outcome: "completed_positive" },
      },
      report: { paper_title: "Real-data study" },
      claim_audit: { total: 4, supported: 4, weakly_supported: 0, unsupported: 0, support_score: 1 },
      steps: [],
      errors: [],
      constraints: { workflow_mode: "auto" },
    } as unknown as ResearchRun, { llm_enabled: true, qwen_model: "qwen-plus" } as PublicConfig);

    expect(readiness.state).toBe("ready");
    expect(readiness.readyCount).toBe(5);
    expect(readiness.score).toBe(100);
  });

  it("labels incomplete report exports as drafts", () => {
    const readiness = buildCompetitionReadiness(null, {
      llm_enabled: false,
      qwen_model: "qwen-plus",
    } as PublicConfig);

    expect(reportExportNotice(readiness)).toEqual({
      tone: "blocked",
      title: "当前导出为可信性草稿",
      detail: "研究可信度 0/100；请先补齐红色检查项。",
    });
  });

  it("does not warn before exporting a fully ready report", () => {
    expect(reportExportNotice({ state: "ready", score: 100, readyCount: 5, checks: [] })).toBeNull();
  });

  it("prefers a direct arXiv PDF without browser capture", () => {
    expect(resolvePaperReadTarget({
      pdf_url: null,
      source_url: "https://arxiv.org/abs/2401.12345",
      arxiv_id: "2401.12345v2",
    })).toEqual({
      kind: "embedded_pdf",
      url: "https://arxiv.org/pdf/2401.12345v2",
    });
  });

  it("uses metadata-only reading when no direct PDF is known", () => {
    expect(resolvePaperReadTarget({
      pdf_url: null,
      source_url: "https://publisher.example/paper/42",
      arxiv_id: null,
    })).toEqual({
      kind: "source_only",
      url: "https://publisher.example/paper/42",
    });
  });

  it("uses a concrete research name instead of the run id", () => {
    expect(runDisplayName({
      display_name: "",
      question: "  基于真实波形数据的   地震事件分类可信研究  ",
    })).toBe("基于真实波形数据的 地震事件分类可信研究");
  });

  it("offers lifecycle actions that match the run state", () => {
    expect(runHistoryActions({ status: "running", control_action: "none", pause_reason: null })).toEqual(["pause", "abandon"]);
    expect(runHistoryActions({ status: "running", control_action: "pause", pause_reason: null })).toEqual(["abandon"]);
    expect(runHistoryActions({ status: "paused", control_action: "none", pause_reason: "user" })).toEqual(["resume", "abandon"]);
    expect(runHistoryActions({ status: "paused", control_action: "none", pause_reason: "review" })).toEqual(["review", "abandon"]);
    expect(runHistoryActions({ status: "abandoned", control_action: "abandon", pause_reason: null })).toEqual([]);
  });
});
