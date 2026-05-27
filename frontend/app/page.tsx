"use client";

import { useEffect, useMemo, useState } from "react";
import { Beaker, FileSearch, FlaskConical, Play, RefreshCw, ShieldCheck } from "lucide-react";
import { createRun, getRun, ResearchRun, startRun } from "../lib/api";

const defaultQuestion =
  "请围绕固态电解质材料的离子电导率与稳定性提升，基于真实文献和开放数据库，生成可验证科学假设与实验计划。";

export default function Home() {
  const [question, setQuestion] = useState(defaultQuestion);
  const [domain, setDomain] = useState("energy_materials");
  const [maxPapers, setMaxPapers] = useState(6);
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!run || !["running", "created"].includes(run.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getRun(run.run_id);
        setRun(next);
      } catch {
        window.clearInterval(timer);
      }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [run?.run_id, run?.status]);

  const reportPreview = useMemo(() => {
    if (!run?.report) return "报告生成后会显示 Problem Statement、Rationale、Methods、Results 与 Citation Audit Log。";
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
      "Citation Audit Log:",
      ...run.report.citation_audit_log.map((item) => `- ${item}`)
    ].join("\n");
  }, [run]);

  async function handleStart() {
    setBusy(true);
    setError("");
    try {
      const created = await createRun(question, domain, maxPapers);
      setRun(created);
      const started = await startRun(created.run_id);
      setRun(started);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    if (!run) return;
    setRun(await getRun(run.run_id));
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Beaker size={19} /></div>
          <span>TrustSci Agent</span>
        </div>
        <div className="form">
          <div className="field">
            <label className="label">领域</label>
            <select className="select" value={domain} onChange={(event) => setDomain(event.target.value)}>
              <option value="energy_materials">能源材料</option>
              <option value="biomedicine">生物医学</option>
              <option value="climate_remote_sensing">气候与遥感</option>
              <option value="custom">自定义</option>
            </select>
          </div>
          <div className="field">
            <label className="label">科研问题</label>
            <textarea className="textarea" value={question} onChange={(event) => setQuestion(event.target.value)} />
          </div>
          <div className="field">
            <label className="label">最大论文数</label>
            <input
              className="input"
              min={3}
              max={12}
              type="number"
              value={maxPapers}
              onChange={(event) => setMaxPapers(Number(event.target.value))}
            />
          </div>
          <button className="primary" onClick={handleStart} disabled={busy}>
            {busy ? <RefreshCw size={17} /> : <Play size={17} />}
            启动工作流
          </button>
          {run && (
            <button className="secondary" onClick={refresh}>
              <RefreshCw size={16} />
              刷新状态
            </button>
          )}
          {error && <span className="badge warn">{error}</span>}
        </div>
      </aside>

      <section className="content">
        <div className="topbar">
          <div className="title-block">
            <h1>可信多智能体 AI Scientist 工作台</h1>
            <p>从真实文献检索、引用核验、证据链构建，到假设辩论、实验设计和比赛格式报告输出。</p>
          </div>
          <span className="badge">{run ? `${run.status} / ${run.current_stage}` : "idle"}</span>
        </div>

        <div className="grid">
          <section className="panel span-4">
            <h2>Run Timeline</h2>
            <div className="progress"><div style={{ width: `${Math.round((run?.progress || 0) * 100)}%` }} /></div>
            <div className="timeline" style={{ marginTop: 14 }}>
              {(run?.steps || []).map((step) => (
                <div className="step" key={step.name}>
                  <span className={`dot ${step.status}`} />
                  <span>{step.name}</span>
                  <span className="badge">{step.status}</span>
                  {step.summary && <span className="muted" style={{ gridColumn: "2 / 4" }}>{step.summary}</span>}
                </div>
              ))}
              {!run?.steps.length && <p className="muted">启动后会逐步展示 Planner、检索、核验、辩论和报告写作进度。</p>}
            </div>
          </section>

          <section className="panel span-8">
            <h2><FileSearch size={16} /> Evidence Board</h2>
            <div className="list">
              {(run?.evidence || []).slice(0, 6).map((item) => (
                <article className="item" key={item.evidence_id}>
                  <div className="item-title">{item.claim}</div>
                  <div className="item-meta">{item.source_title}</div>
                  <p className="muted">{item.quote_or_summary}</p>
                  <span className={`badge ${item.verified ? "good" : "warn"}`}>
                    {item.verified ? "verified" : "needs audit"}
                  </span>
                </article>
              ))}
              {!run?.evidence.length && <p className="muted">证据项会绑定论文、DOI、摘要或全文片段，并进入最终引用白名单。</p>}
            </div>
          </section>

          <section className="panel span-6">
            <h2><ShieldCheck size={16} /> Citation Verifier</h2>
            <div className="list">
              {(run?.papers || []).map((paper) => (
                <article className="item" key={paper.paper_id}>
                  <div className="item-title">{paper.title}</div>
                  <div className="item-meta">{paper.year || "n.d."} · DOI {paper.doi || "N/A"}</div>
                  <span className={`badge ${paper.verification_status === "verified" ? "good" : "warn"}`}>
                    {paper.verification_status}
                  </span>
                </article>
              ))}
              {!run?.papers.length && <p className="muted">系统会优先从 OpenAlex 获取候选论文，再用 Crossref 做 DOI 和标题相似度核验。</p>}
            </div>
          </section>

          <section className="panel span-6">
            <h2>Scientific Data</h2>
            <div className="list">
              {(run?.data_profiles || []).slice(0, 4).map((profile) => (
                <article className="item" key={profile.name}>
                  <div className="item-title">{profile.name}</div>
                  <div className="item-meta">
                    {profile.source} · {profile.rows ? `${profile.rows} rows` : profile.availability}
                  </div>
                  <p className="muted">{profile.target || "no target"} · {profile.task_type}</p>
                </article>
              ))}
              {run?.baseline_result_card && (
                <article className="item">
                  <div className="item-title">{run.baseline_result_card.name}</div>
                  <div className="item-meta">
                    {Object.entries(run.baseline_result_card.metrics).map(([key, value]) => `${key} ${value}`).join(" · ")}
                  </div>
                  <p className="muted">{run.baseline_result_card.result_summary}</p>
                </article>
              )}
              {!run?.data_profiles?.length && <p className="muted">这里会展示 Matbench 元数据、Materials Project adapter 状态和 baseline result card。</p>}
            </div>
          </section>

          <section className="panel span-6">
            <h2><FlaskConical size={16} /> Hypothesis Arena</h2>
            <div className="list">
              {(run?.hypotheses || []).map((hypothesis) => (
                <article className="item" key={hypothesis.hypothesis_id}>
                  <div className="item-title">{hypothesis.hypothesis_id}: {hypothesis.statement}</div>
                  {hypothesis.critic && (
                    <p className="muted">
                      novelty {hypothesis.critic.novelty}/10 · verifiability {hypothesis.critic.verifiability}/10 · {hypothesis.critic.risk}
                    </p>
                  )}
                  <span className={`badge ${hypothesis.selected ? "good" : ""}`}>
                    {hypothesis.selected ? "selected" : "candidate"}
                  </span>
                </article>
              ))}
              {!run?.hypotheses.length && <p className="muted">候选假设会经过 Critic Agent 评分与修订建议，再进入实验设计。</p>}
            </div>
          </section>

          <section className="panel span-12">
            <h2>Final Report</h2>
            <div className="report">{reportPreview}</div>
          </section>
        </div>
      </section>
    </main>
  );
}
