"use client";

import { useState } from "react";
import { Download, ShieldAlert } from "lucide-react";
import { FormalReport, PublicConfig, reportExportUrl, ResearchRun } from "../../lib/api";
import { buildCompetitionReadiness, reportExportNotice } from "../../lib/workbench";

type ReportTab = "english" | "chinese" | "audit";

export function ReportViewer({ run, config }: { run: ResearchRun | null; config: PublicConfig | null }) {
  const [tab, setTab] = useState<ReportTab>("chinese");
  const hasReport = Boolean(run?.report);
  const exportNotice = reportExportNotice(buildCompetitionReadiness(run, config));

  return (
    <section className="panel span-12">
      <div className="panel-heading">
        <h2>最终研究报告</h2>
        {hasReport && (
          <div className="actions">
            <a className="secondary link-button" href={reportExportUrl(run!.run_id, "md")}>
              <Download size={15} />
              Markdown
            </a>
            <a className="secondary link-button" href={reportExportUrl(run!.run_id, "json")}>
              <Download size={15} />
              JSON
            </a>
            <a className="secondary link-button" href={reportExportUrl(run!.run_id, "pdf")}>
              <Download size={15} />
              PDF
            </a>
          </div>
        )}
      </div>

      {hasReport && exportNotice && (
        <div className={`report-export-notice ${exportNotice.tone}`}>
          <ShieldAlert size={18} />
          <span>
            <strong>{exportNotice.title}</strong>
            <small>{exportNotice.detail}</small>
          </span>
        </div>
      )}

      <div className="segmented">
        <button className={tab === "chinese" ? "active" : ""} onClick={() => setTab("chinese")}>
          中文报告
        </button>
        <button className={tab === "english" ? "active" : ""} onClick={() => setTab("english")}>
          英文报告
        </button>
        <button className={tab === "audit" ? "active" : ""} onClick={() => setTab("audit")}>
          审计附录
        </button>
      </div>

      <div className="report">{buildReportPreview(run, tab)}</div>
    </section>
  );
}

function buildReportPreview(run: ResearchRun | null, tab: ReportTab) {
  if (!run?.report) return "报告尚未生成。";
  if (tab === "english") {
    return run.report.english_report
      ? renderFormalReport(run.report.english_report, "english")
      : buildLegacyReportPreview(run);
  }
  if (tab === "chinese") {
    return run.report.chinese_report
      ? renderFormalReport(run.report.chinese_report, "chinese")
      : "中文报告尚未生成。可以先查看英文报告或等待报告翻译阶段完成。";
  }
  return renderAuditAppendix(run);
}

function renderFormalReport(report: FormalReport, language: "english" | "chinese") {
  const headings =
    language === "english"
      ? {
          report: "英文报告",
          title: "Paper Title",
          abstract: "Paper Abstract",
          problem: "Problem Statement",
          rationale: "Rationale",
          technical: "Technical Details",
          datasets: "Datasets",
          source: "Source",
          target: "Target",
          methods: "Methods",
          experiments: "Experiments",
          baselines: "Baselines",
          metrics: "Metrics",
          design: "Experimental Design",
          results: "Results",
          executed: "Executed Results",
          expected: "Expected Validation Outcomes",
          limitations: "Limitations and Risk Controls",
          references: "References"
        }
      : {
          report: "中文报告",
          title: "标题",
          abstract: "摘要",
          problem: "待研究问题",
          rationale: "解决思路",
          technical: "必要技术手段",
          datasets: "数据集",
          source: "Source：假设推演依据的历史数据",
          target: "Target：验证实验所需的拟采集数据特征",
          methods: "方法论",
          experiments: "实验设计",
          baselines: "基线对比",
          metrics: "评估指标",
          design: "实验流程",
          results: "实验结果",
          executed: "已执行结果",
          expected: "预期验证结果",
          limitations: "局限性与风险控制",
          references: "参考论文"
        };

  return [
    `# ${headings.report}`,
    "",
    `## 1. ${headings.title}`,
    report.paper_title,
    "",
    `## 2. ${headings.abstract}`,
    report.paper_abstract,
    "",
    `## 3. ${headings.problem}`,
    report.problem_statement,
    "",
    `## 4. ${headings.rationale}`,
    report.rationale,
    "",
    `## 5. ${headings.technical}`,
    report.technical_details,
    "",
    `## 6. ${headings.datasets}`,
    "",
    `### 6.1 ${headings.source}`,
    report.datasets.source,
    "",
    `### 6.2 ${headings.target}`,
    report.datasets.target,
    "",
    `## 7. ${headings.methods}`,
    report.methods,
    "",
    `## 8. ${headings.experiments}`,
    "",
    `### 8.1 ${headings.baselines}`,
    report.experiments.baselines,
    "",
    `### 8.2 ${headings.metrics}`,
    report.experiments.metrics,
    "",
    `### 8.3 ${headings.design}`,
    report.experiments.design,
    "",
    `## 9. ${headings.results}`,
    "",
    `### 9.1 ${headings.executed}`,
    report.results.executed_results,
    "",
    `### 9.2 ${headings.expected}`,
    report.results.expected_validation_outcomes,
    "",
    `## 10. ${headings.limitations}`,
    report.limitations_and_risk_controls,
    "",
    `## 11. ${headings.references}`,
    ...renderReferences(report.references)
  ].join("\n");
}

function renderAuditAppendix(run: ResearchRun) {
  const provenance = run.report?.system_provenance;
  return [
    "# 系统溯源与审计附录",
    "",
    "## Agent 工作流",
    ...((provenance?.agent_workflow || run.steps).map((step) => {
      const item = step as Record<string, unknown>;
      return `- ${String(item.name || "unknown")}：${String(item.status || "unknown")} - ${String(item.summary || "")}`;
    }) || ["- 没有记录工作流。"]),
    "",
    "## 证据账本",
    ...((provenance?.evidence_ledger || run.evidence).slice(0, 40).map((item) => {
      const entry = item as Record<string, unknown>;
      return `- ${String(entry.evidence_id || "")}：${String(entry.claim || "")}（已核验=${String(
        entry.verified
      )}，可进报告=${String(entry.eligible_for_report)}）`;
    }) || ["- 没有记录证据。"]),
    "",
    "## 引用审计日志",
    ...((provenance?.citation_audit_log || run.report?.citation_audit_log || []).map((item) => `- ${item}`) || [
      "- 没有引用审计日志。"
    ]),
    "",
    "## 结论核验摘要",
    run.claim_audit
      ? `已支持 ${run.claim_audit.supported}/${run.claim_audit.total}，弱支持 ${run.claim_audit.weakly_supported}，不支持 ${run.claim_audit.unsupported}，支持分 ${run.claim_audit.support_score}`
      : "结论核验待生成。",
    "",
    "## 运行元数据",
    JSON.stringify(provenance?.run_metadata || { run_id: run.run_id, status: run.status }, null, 2)
  ].join("\n");
}

function buildLegacyReportPreview(run: ResearchRun) {
  if (!run.report) return "报告尚未生成。";
  return [
    `# ${run.report.paper_title}`,
    "",
    `待研究问题：${run.report.problem_statement}`,
    "",
    `解决思路：${run.report.rationale}`,
    "",
    "方法：",
    ...run.report.methods.map((item) => `- ${item}`),
    "",
    `结果：${run.report.results}`,
    "",
    "引用审计日志：",
    ...run.report.citation_audit_log.map((item) => `- ${item}`)
  ].join("\n");
}

function renderReferences(references: FormalReport["references"]) {
  if (!references.length) return ["- 没有可进入报告的已核验参考文献。"];
  return references.map((paper) => {
    const id = paper.doi || paper.arxiv_id || paper.openalex_id || paper.source_url || "N/A";
    const confidence = paper.verification_confidence ?? "n/a";
    return `- ${paper.title} (${paper.year || "n.d."}). ID: ${id}. 核验：${
      paper.verification_method || paper.verification_status
    }; 置信度=${confidence}.`;
  });
}
