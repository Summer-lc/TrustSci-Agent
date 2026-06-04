import { Download } from "lucide-react";
import { reportExportUrl, ResearchRun } from "../../lib/api";

export function ReportViewer({ run }: { run: ResearchRun | null }) {
  const reportPreview = buildReportPreview(run);
  return (
    <section className="panel span-12">
      <div className="panel-heading">
        <h2>Final Report</h2>
        {run?.report && (
          <div className="actions">
            <a className="secondary link-button" href={reportExportUrl(run.run_id, "md")}>
              <Download size={15} />
              Markdown
            </a>
            <a className="secondary link-button" href={reportExportUrl(run.run_id, "json")}>
              <Download size={15} />
              JSON
            </a>
          </div>
        )}
      </div>
      <div className="report">{reportPreview}</div>
    </section>
  );
}

function buildReportPreview(run: ResearchRun | null) {
  if (!run?.report) return "报告尚未生成。";
  return [
    `# ${run.report.paper_title}`,
    "",
    `Problem Statement: ${run.report.problem_statement}`,
    "",
    `Rationale: ${run.report.rationale}`,
    "",
    "Methods:",
    ...run.report.methods.map((item) => `- ${item}`),
    "",
    `Results: ${run.report.results}`,
    "",
    run.citation_report
      ? `Citation Verification: verified ${run.citation_report.verified}/${run.citation_report.total}, integrity ${run.citation_report.integrity_score}`
      : "Citation Verification: pending",
    "",
    run.claim_audit
      ? `Claim Audit: supported ${run.claim_audit.supported}/${run.claim_audit.total}, weak ${run.claim_audit.weakly_supported}, unsupported ${run.claim_audit.unsupported}, support ${run.claim_audit.support_score}`
      : "Claim Audit: pending",
    "",
    "Citation Audit Log:",
    ...run.report.citation_audit_log.map((item) => `- ${item}`)
  ].join("\n");
}
