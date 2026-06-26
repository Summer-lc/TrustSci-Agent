import { Globe, RefreshCw } from "lucide-react";
import { BrowserCaptureResult } from "../../lib/api";

export function BrowserCapturePanel({
  url,
  result,
  busy,
  error,
  canIngestPdf,
  onUrlChange,
  onCapture,
  onIngestPdf
}: {
  url: string;
  result: BrowserCaptureResult | null;
  busy: boolean;
  error: string;
  canIngestPdf: boolean;
  onUrlChange: (value: string) => void;
  onCapture: () => void;
  onIngestPdf: (path: string) => void;
}) {
  return (
    <section className="panel span-6">
      <h2><Globe size={16} /> 浏览器采集 / Browser Capture</h2>
      <div className="inline-form">
        <input className="input" value={url} onChange={(event) => onUrlChange(event.target.value)} />
        <button className="secondary" onClick={onCapture} disabled={busy}>
          {busy ? <RefreshCw size={15} /> : <Globe size={15} />}
          采集 / Capture
        </button>
      </div>
      {error && <p className="muted warn-text">{error}</p>}
      {result && (
        <div className="dense">
          <div className="item-title">{result.title}</div>
          <div className="item-meta">{result.domain} · {result.status_code || "n/a"}</div>
          <p className="muted">HTML {result.html_path}</p>
          <p className="muted">Screenshot {result.screenshot_path}</p>
          <p className="muted">PDF links {result.pdf_links.length} · downloads {result.downloaded_pdfs.length}</p>
          {result.downloaded_pdfs.map((pdf, index) => (
            <div className="item compact" key={`${pdf.path || pdf.url || index}`}>
              <div className="item-meta">{String(pdf.path || pdf.url || "PDF")}</div>
              {"path" in pdf && typeof pdf.path === "string" && (
                <button className="secondary" onClick={() => onIngestPdf(pdf.path as string)} disabled={!canIngestPdf}>
                  入账证据 / Ingest
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
