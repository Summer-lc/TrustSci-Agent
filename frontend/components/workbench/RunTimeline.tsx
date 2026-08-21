import { ResearchRun } from "../../lib/api";

const stepLabels: Record<string, string> = {
  intent_router: "意图识别",
  planner: "任务规划",
  literature_search: "文献检索",
  citation_verification: "引用核验",
  evidence_ledger: "证据入账",
  literature_mining: "文献挖掘",
  paper_classification: "论文分类",
  scientific_data_profile: "数据画像",
  hypothesis_debate: "假设评审",
  arena: "假设竞技",
  novelty_check: "新颖性检查",
  extract_code_urls: "代码链接提取",
  baseline_discover: "Baseline 发现",
  baseline_verify: "Baseline 验证",
  baseline_quality_gate: "Baseline 质量门",
  re_search_literature: "补充检索",
  experiment_design: "实验设计",
  code_experiment: "写代码并运行",
  macro_react: "宏观修复判断",
  report_writer: "报告生成",
  claim_verification: "结论核验",
  report_revision: "报告修订",
  claim_reverification: "结论复核",
  report_translation: "报告翻译",
};

const statusLabels: Record<string, string> = {
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  paused: "已暂停",
  created: "已创建",
};

export function RunTimeline({ run, compact = false }: { run: ResearchRun | null; compact?: boolean }) {
  const activeStep = run?.steps.find((step) => step.status === "running");
  const progress = Math.round((run?.progress || 0) * 100);

  if (compact) {
    return (
      <section className="sidebar-section workflow-summary">
        <div className="section-title">
          <span>运行进度</span>
          <span className="badge">{run ? `${progress}%` : "空闲"}</span>
        </div>
        <div className="progress"><div style={{ width: `${progress}%` }} /></div>
        <div className="mini-timeline">
          {(run?.steps || []).map((step) => (
            <div className="mini-step" key={step.name} title={step.summary || step.name}>
              <span className={`dot ${step.status}`} />
              <span>{stepLabels[step.name] || step.name}</span>
            </div>
          ))}
          {!run?.steps.length && <span className="muted compact">等待任务启动</span>}
        </div>
        {activeStep && (
          <p className="muted compact">当前：{stepLabels[activeStep.name] || activeStep.name}</p>
        )}
      </section>
    );
  }

  return (
    <section className="panel span-12">
      <h2>运行时间线</h2>
      <div className="progress"><div style={{ width: `${progress}%` }} /></div>
      {activeStep && (
        <div className="callout" style={{ marginTop: 14 }}>
          <strong>当前工作：{stepLabels[activeStep.name] || activeStep.name}</strong>
          <p className="muted">{activeStep.summary || "正在运行工作流步骤。"}</p>
        </div>
      )}
      <div className="timeline" style={{ marginTop: 14 }}>
        {(run?.steps || []).map((step) => (
          <div className="step" key={step.name}>
            <span className={`dot ${step.status}`} />
            <span>{stepLabels[step.name] || step.name}</span>
            <span className="badge">{statusLabels[step.status] || step.status}</span>
            {step.summary && <span className="muted" style={{ gridColumn: "2 / 4" }}>{step.summary}</span>}
          </div>
        ))}
        {!run?.steps.length && <p className="muted">等待任务启动</p>}
      </div>
      {Boolean(run?.errors?.length) && (
        <div className="callout danger" style={{ marginTop: 14 }}>
          <strong>工作流错误</strong>
          {run?.errors.map((error, index) => <p className="muted" key={`${error}-${index}`}>{error}</p>)}
        </div>
      )}
    </section>
  );
}
