export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type ResearchRun = {
  run_id: string;
  domain: string;
  question: string;
  status: string;
  current_stage: string;
  progress: number;
  plan: Record<string, unknown>;
  steps: Array<{ name: string; status: string; summary: string }>;
  papers: Array<{
    paper_id: string;
    title: string;
    year?: number;
    doi?: string;
    verification_status: string;
    title_match_score?: number;
  }>;
  evidence: Array<{
    evidence_id: string;
    claim: string;
    source_title: string;
    verified: boolean;
    quote_or_summary: string;
  }>;
  data_profiles: Array<{
    name: string;
    source: string;
    source_url?: string;
    rows?: number;
    fields: string[];
    target?: string;
    task_type: string;
    availability: string;
    notes: string;
  }>;
  baseline_result_card?: {
    name: string;
    dataset: string;
    target: string;
    model: string;
    train_rows: number;
    test_rows: number;
    metrics: Record<string, number>;
    result_summary: string;
    artifact_path?: string;
  };
  hypotheses: Array<{
    hypothesis_id: string;
    statement: string;
    revised_statement?: string;
    selected: boolean;
    critic?: {
      novelty: number;
      self_consistency: number;
      verifiability: number;
      data_availability: number;
      risk: string;
      revision_advice: string;
    };
  }>;
  experiment_plan?: {
    datasets: string[];
    source: string;
    target: string;
    baselines: string[];
    metrics: string[];
    experiment_steps: string[];
    expected_results: string;
    failure_modes: string[];
  };
  report?: {
    paper_title: string;
    problem_statement: string;
    rationale: string;
    methods: string[];
    results: string;
    baseline_result_card?: {
      name: string;
      metrics: Record<string, number>;
      result_summary: string;
    };
    citation_audit_log: string[];
  };
};

export async function createRun(question: string, domain: string, maxPapers: number) {
  const response = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      domain,
      question,
      constraints: {
        must_verify_citations: true,
        max_papers: maxPapers,
        require_experiment_plan: true,
        enable_browser_worker: false
      }
    })
  });
  if (!response.ok) throw new Error("Failed to create run");
  return (await response.json()) as ResearchRun;
}

export async function startRun(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/start`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to start run");
  return (await response.json()) as ResearchRun;
}

export async function getRun(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load run");
  return (await response.json()) as ResearchRun;
}
