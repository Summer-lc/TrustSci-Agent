import {
  BookCheck,
  CheckCircle2,
  CircleAlert,
  Cpu,
  Database,
  FileCheck2,
  FlaskConical,
  ShieldCheck,
  ChevronDown,
} from "lucide-react";

import { PublicConfig, ResearchRun } from "../../lib/api";
import {
  buildCompetitionReadiness,
  CompetitionReadinessCheck,
  ReadinessStatus,
} from "../../lib/workbench";

const CHECK_ICONS = {
  qwen: Cpu,
  dataset: Database,
  references: BookCheck,
  experiment: FlaskConical,
  report: FileCheck2,
};

export function CompetitionReadinessPanel({
  run,
  config,
}: {
  run: ResearchRun | null;
  config: PublicConfig | null;
}) {
  const readiness = buildCompetitionReadiness(run, config);

  return (
    <details className={`competition-readiness ${readiness.state}`} aria-label="研究可信度">
      <summary className="readiness-summary">
        <div className="readiness-heading">
          <span className="readiness-icon"><ShieldCheck size={18} /></span>
          <span>
            <small>RESEARCH TRUST</small>
            <strong>研究可信检查</strong>
          </span>
        </div>
        <div className="readiness-score" aria-label={`可信度 ${readiness.score} 分`}>
          <strong>{readiness.score}</strong>
          <span>/ 100</span>
        </div>
        <div className="readiness-progress" aria-hidden="true">
          <span style={{ width: `${readiness.score}%` }} />
        </div>
        <p>{summaryText(readiness.state, readiness.readyCount)}</p>
        <ChevronDown className="readiness-chevron" size={18} aria-hidden="true" />
      </summary>

      <div className="readiness-checks">
        {readiness.checks.map((check) => (
          <ReadinessItem check={check} key={check.id} />
        ))}
      </div>
    </details>
  );
}

function ReadinessItem({ check }: { check: CompetitionReadinessCheck }) {
  const Icon = CHECK_ICONS[check.id];
  return (
    <article className={`readiness-item ${check.status}`}>
      <span className="readiness-item-icon"><Icon size={16} /></span>
      <span className="readiness-item-copy">
        <strong>{check.label}</strong>
        <small>{check.detail}</small>
      </span>
      <span className="readiness-state-icon" aria-label={statusText(check.status)}>
        {check.status === "ready" ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}
      </span>
    </article>
  );
}

function summaryText(state: ReadinessStatus, readyCount: number) {
  if (state === "ready") return "五项可信检查均已满足，可以整理正式研究材料。";
  if (state === "warning") return `${readyCount}/5 项已满足，仍有内容需要人工核验。`;
  return `${readyCount}/5 项已满足；当前结果仅适合开发或演示，不应作为正式科研结论。`;
}

function statusText(status: ReadinessStatus) {
  if (status === "ready") return "已满足";
  if (status === "warning") return "待核验";
  return "未满足";
}
