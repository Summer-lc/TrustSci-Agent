import { BookOpen, ChevronRight } from "lucide-react";
import { ResearchRun } from "../../lib/api";

export function LiteratureBoard({
  run,
  selectedPaperId,
  onSelectPaper
}: {
  run: ResearchRun | null;
  selectedPaperId?: string | null;
  onSelectPaper?: (paperId: string) => void;
}) {
  const papers = run?.papers || [];
  const isSeismicRun = run?.domain === "seismic_event_classification";
  const citationDone = stepCompleted(run, "citation_verification");
  const classificationDone = !isSeismicRun || stepCompleted(run, "paper_classification");
  const sourceCounts = papers.reduce<Record<string, number>>((acc, paper) => {
    const source = paper.source_api || "unknown";
    acc[source] = (acc[source] || 0) + 1;
    return acc;
  }, {});
  const verified = papers.filter((paper) => paper.verification_status === "verified").length;

  return (
    <section className="panel span-12">
      <div className="panel-heading">
        <h2><BookOpen size={16} /> 文献列表</h2>
        <div className="actions">
          <span className="badge">{papers.length} 篇论文</span>
          <span className={`badge ${verified ? "good" : "warn"}`}>已核验 {verified}</span>
        </div>
      </div>
      <div className="metric-row">
        {Object.entries(sourceCounts).map(([source, count]) => (
          <span className="badge" key={source}>{source} {count}</span>
        ))}
        {!papers.length && <span className="badge warn">等待文献检索</span>}
      </div>
      <div className="evidence-table" role="table" aria-label="文献证据矩阵">
        <div className="evidence-table-head" role="row">
          <span role="columnheader">论文</span>
          <span role="columnheader">来源 / 年份</span>
          <span role="columnheader">引用核验</span>
          <span role="columnheader">报告资格</span>
          <span role="columnheader">任务相关性</span>
          <span aria-hidden="true" />
        </div>
        {papers.slice(0, 8).map((paper) => (
          <button
            className={`evidence-row ${selectedPaperId === paper.paper_id ? "active" : ""}`}
            key={paper.paper_id}
            onClick={() => onSelectPaper?.(paper.paper_id)}
            type="button"
            role="row"
            aria-pressed={selectedPaperId === paper.paper_id}
          >
            <span className="evidence-paper" role="cell">
              <strong>{paper.title}</strong>
              <small>
                {paper.venue || "未知期刊"}
                {paper.authors.length ? ` · ${paper.authors.slice(0, 2).join(", ")}` : ""}
                {paper.cited_by_count !== undefined ? ` · 被引 ${paper.cited_by_count}` : ""}
              </small>
            </span>
            <span className="evidence-source" role="cell">
              <strong>{paper.source_api || "未知来源"}</strong>
              <small>{paper.year || paper.publication_date || "未知年份"}</small>
            </span>
            <span role="cell">
              <span className={`evidence-state ${citationDone && paper.verification_status === "verified" ? "good" : citationDone ? "warn" : "pending"}`}>
                {citationDone ? verificationLabel(paper.verification_status) : "引用待核验"}
              </span>
            </span>
            <span role="cell">
              <span className={`evidence-state ${citationDone && paper.report_eligible ? "good" : citationDone ? "warn" : "pending"}`}>
                {citationDone ? (paper.report_eligible ? "可进报告" : "仅审计") : "报告资格待定"}
              </span>
            </span>
            <span role="cell">
              {classificationDone ? (
                <span className={`evidence-state ${paper.seismic_relevant ? "good" : "warn"}`}>
                  {isSeismicRun ? (paper.seismic_relevant ? "地震相关" : "非地震相关") : paper.paper_role ? paperRoleLabel(paper.paper_role) : "通用研究"}
                </span>
              ) : <span className="evidence-state pending">等待分类</span>}
            </span>
            <ChevronRight className="evidence-row-arrow" size={17} aria-hidden="true" />
          </button>
        ))}
        {!papers.length && <p className="evidence-empty muted">暂无文献候选。启动研究后，检索结果会在这里形成可核验的证据矩阵。</p>}
      </div>
    </section>
  );
}

function stepCompleted(run: ResearchRun | null, name: string) {
  return Boolean(run?.steps?.some((step) => step.name === name && step.status === "completed"));
}

function verificationLabel(status: string) {
  if (status === "verified") return "已核验";
  if (status === "hallucinated") return "疑似幻觉";
  if (status === "partial") return "部分匹配";
  if (status === "suspicious") return "可疑";
  return status || "未知";
}

function paperRoleLabel(role: string) {
  if (role === "method_model") return "方法/模型论文";
  if (role === "dataset_benchmark") return "数据集/基准";
  if (role === "survey") return "综述";
  if (role === "application") return "应用论文";
  return role;
}
