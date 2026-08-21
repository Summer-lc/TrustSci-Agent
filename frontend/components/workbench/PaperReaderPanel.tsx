import { ExternalLink, FileText, RefreshCw, ShieldAlert } from "lucide-react";
import { API_BASE, PaperPreviewResult, ResearchRun } from "../../lib/api";
import { resolvePaperReadTarget } from "../../lib/workbench";

type Paper = ResearchRun["papers"][number];

export function PaperReaderPanel({
  paper,
  preview,
  loading,
  error,
  onRetryPreview,
}: {
  paper: Paper | null;
  preview: PaperPreviewResult | null;
  loading: boolean;
  error: string;
  onRetryPreview: () => void;
}) {
  if (!paper) {
    return (
      <section className="panel span-4">
        <div className="panel-heading"><h2><FileText size={16} /> 文献原文</h2></div>
        <p className="muted">点击流程区的文献后，这里会显示摘要、来源链接和原文预览。</p>
      </section>
    );
  }

  const readTarget = resolvePaperReadTarget(paper);
  const pdfUrl = readTarget.kind === "source_only" ? null : readTarget.url;

  return (
    <section className="panel span-4 paper-reader">
      <div className="panel-heading">
        <h2><FileText size={16} /> 文献原文</h2>
        <span className="badge">{paper.source_api || "unknown"}</span>
      </div>
      <div className="item-title">{paper.title}</div>
      <div className="item-meta">
        {paper.year || paper.publication_date || "未知年份"}
        {paper.venue ? ` · ${paper.venue}` : ""}
        {paper.authors?.length ? ` · ${paper.authors.slice(0, 3).join(", ")}` : ""}
      </div>
      <div className="item-meta">
        DOI {paper.doi || "无"}
        {paper.arxiv_id ? ` · arXiv ${paper.arxiv_id}` : ""}
      </div>
      <details className="paper-abstract">
        <summary>查看摘要</summary>
        {paper.abstract ? <p className="muted">{paper.abstract}</p> : <p className="muted">暂无摘要。</p>}
      </details>
      <div className="item-actions">
        {paper.source_url && (
          <a className="secondary link-button" href={paper.source_url} target="_blank" rel="noreferrer">
            <ExternalLink size={14} /> 外部来源
          </a>
        )}
        {pdfUrl && (
          <a className="secondary link-button" href={pdfUrl} target="_blank" rel="noreferrer">
            <FileText size={14} /> 打开 PDF
          </a>
        )}
      </div>
      {readTarget.kind === "embedded_pdf" && readTarget.url ? (
        <iframe className="paper-frame" src={readTarget.url} title={paper.title} loading="lazy" />
      ) : readTarget.kind === "external_pdf" ? (
        <div className="paper-preview-state idle-state">
          <FileText size={20} />
          <p>该 PDF 来源不适合内嵌显示，请使用上方“打开 PDF”。</p>
        </div>
      ) : loading ? (
        <div className="paper-preview-state"><RefreshCw className="spin" size={18} /> 正在抓取论文网页…</div>
      ) : preview?.kind === "web_snapshot" && preview.screenshot_url ? (
        <div className="paper-snapshot-wrap">
          <img className="paper-snapshot" src={`${API_BASE}${preview.screenshot_url}`} alt={`${paper.title} 网页快照`} />
          <span className="muted compact">网页快照{preview.cached ? "（已缓存）" : ""}，仅用于阅读辅助。</span>
        </div>
      ) : (
        <div className={`paper-preview-state ${preview?.error_summary || error ? "error-state" : "idle-state"}`}>
          {preview?.error_summary || error ? <ShieldAlert size={20} /> : <FileText size={20} />}
          <p>{preview?.error_summary || error || "没有可直达的 PDF。为避免人机验证，系统不会自动抓取来源网页。"}</p>
          {paper.source_url && <button type="button" className="secondary" onClick={onRetryPreview}><RefreshCw size={14} /> 手动生成网页快照</button>}
        </div>
      )}
      <p className="muted paper-reader-help">优先使用直接 PDF；来源网站要求验证时，请通过“外部来源”在浏览器中打开。</p>
    </section>
  );
}
