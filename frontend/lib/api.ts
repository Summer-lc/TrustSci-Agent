export interface AcceptanceGate {
  tests_pass: boolean;
  metrics_generated: boolean;
  baseline_comparison_written: boolean;
  all_passed?: boolean;
}
export interface ComparisonResult {
  baseline_source: string;
  baseline_metrics: Record<string, number | Record<string, number>>;
  method_metrics: Record<string, number | Record<string, number>>;
  method_beats_baseline: boolean;
  outcome: "completed_positive" | "completed_negative" | "failed";
  notes: string[];
}
export interface FairComparisonPlan {
  method_name: string;
  baseline_source: string;
  split_strategy: string;
  metrics: string[];
  preprocessing: string;
}
export interface IterEntry {
  round: number;
  phase: "initial" | "repair";
  model_py_hash: string;
  tests_passed: boolean;
  traceback_summary?: string | null;
}
export interface DebugEntry {
  round: number;
  traceback_full?: string | null;
  patch_diff?: string | null;
}
export interface ExperimentSummary {
  outcome: "completed_positive" | "completed_negative" | "failed";
  tests_pass: boolean;
  method_beats_baseline: boolean;
  baseline_source: string;
  best_metric: number | null;
  failure_reason: string | null;
}
export interface CodeExperimentResult {
  harness_version: string;
  model_family: string;
  baseline_source: string;
  model_py_source: string;
  fair_comparison_plan: FairComparisonPlan;
  acceptance_gate: AcceptanceGate;
  comparison: ComparisonResult;
  iteration_log: IterEntry[];
  debug_log: DebugEntry[];
  summary: ExperimentSummary;
}
export type MetricObservation = { name: string; value: number; unit?: string | null; split?: string | null; notes?: string | null };
export type ExperimentAssistanceInput = {
  objective: string; method_summary: string; source_code?: string | null; dataset_description: string;
  baseline_name: string; baseline_metrics: MetricObservation[]; method_metrics: MetricObservation[];
  ablations: Array<{ component: string; metrics: MetricObservation[]; notes?: string | null }>;
  logs: string[]; author_notes: string;
};
export type ResultEvaluation = { verdict: "pass" | "partial" | "fail"; metric_deltas: Array<{name:string;baseline?:number|null;method?:number|null;delta?:number|null}>; supported_claims:string[]; unsupported_claims:string[]; data_quality_warnings:string[]; reasoning:string };
export type AblationAnalysis = { coverage:"complete"|"partial"|"missing"; findings:Array<Record<string,unknown>>; missing_comparisons:string[]; summary:string };
export type ResultInterpretation = { conclusions:string[]; limitations:string[]; failure_explanation?:string|null; next_experiments:string[]; evidence_boundary:string };

export interface NoveltyVerdict {
  verdict: "novel" | "transfer_applicability" | "already_done" | "dataset_only" | "similar_work";
  claim_revision?: string | null;
  prior_art_paper_ids: string[];
  overlap_points: string[];
  retainable_novelty: string[];
  reasoning: string;
  similar_work: Record<string, unknown>[];
  has_public_code: boolean;
}
export interface BaselineGateStatus {
  external_verified_model_baselines: number;
  comparable_count: number;
  run_gate_passed: boolean;
  research_gate_passed: boolean;
  insufficient_reasons: string[];
  comparison_grade: "research" | "degraded";
}

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type PublicConfig = {
  qwen_model: string;
  llm_enabled: boolean;
  dashscope_base_url: string;
  max_papers: number;
  data_dir: string;
  browser_worker_url: string;
  materials_project_configured: boolean;
  semantic_scholar_configured: boolean;
  arxiv_available: boolean;
  cors_origins: string[];
};

export type DatasetProfile = {
  name: string;
  source: string;
  source_url?: string;
  rows?: number;
  fields: string[];
  target?: string;
  task_type: string;
  availability: string;
  notes: string;
};

export type BaselineResultCard = {
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

export type BrowserCaptureResult = {
  trace_id: string;
  url: string;
  domain: string;
  status_code?: number;
  title: string;
    html_path: string;
    screenshot_path: string;
    blocked_reason?: string | null;
  links: Array<Record<string, string>>;
  pdf_links: Array<Record<string, string>>;
  downloaded_pdfs: Array<Record<string, string | number>>;
};

export type PaperPreviewResult = {
  paper_id: string;
  source_url: string;
  kind: "web_snapshot" | "metadata_only";
  title: string;
  screenshot_url?: string | null;
  original_url: string;
  cached: boolean;
  error_summary?: string | null;
};

export type RunStepAction = "retry" | "skip";

export type RestorableWorkspace = {
  run_id: string;
  display_name?: string;
  domain: string;
  question: string;
  status: string;
  current_stage: string;
  control_action?: "none" | "pause" | "abandon";
  pause_reason?: "user" | "review" | "error" | null;
  updated_at?: string;
  workspace_path: string;
};

export type BaselineStrategy = "manual_upload" | "ai_generated" | "none";

export type BaselineMetricObservation = {
  name: string;
  value: number;
  unit?: string | null;
  split?: string | null;
  notes?: string | null;
};

export type ManualBaselineInput = {
  name: string;
  description: string;
  code_text?: string | null;
  repository_url?: string | null;
  run_command?: string | null;
  dataset_description: string;
  metrics: BaselineMetricObservation[];
  notes: string;
};

export type BaselineIntakeRequest = {
  strategy: BaselineStrategy;
  manual?: ManualBaselineInput | null;
};

export type BaselineIntake = {
  strategy: BaselineStrategy;
  source_type: "manual_upload" | "ai_generated" | "unavailable";
  trust_level: "user_provided" | "runnable_demo" | "insufficient";
  name: string;
  description: string;
  metrics: BaselineMetricObservation[];
  limitations: string[];
  provenance_notes: string[];
};

export type ResearchRun = {
  run_id: string;
  display_name: string;
  created_at?: string;
  updated_at?: string;
  domain: string;
  question: string;
  mode: "discovery" | "idea_refinement" | "experiment_assistance";
  idea_brief?: {
    research_problem: string;
    user_idea?: string;
    target_task: string;
    input_data: string[];
    proposed_method?: string;
    expected_contribution?: string;
    target_labels: string[];
    unknowns: string[];
    risks: string[];
  };
  seismic_data_profile?: {
    dataset_name: string;
    num_events: number;
    labels: Record<string, number>;
    channels: string[];
    sampling_rate?: number;
    window_seconds?: number;
    split_strategy: string;
    risks: string[];
    source_path?: string;
  };
  intent?: {
    mode: string;
    confidence: number;
    reason: string;
  };
  baseline_strategy?: BaselineStrategy;
  manual_baseline?: BaselineIntakeRequest | null;
  baseline_intake?: BaselineIntake | null;
  baseline_candidates?: Array<{
    baseline_id: string;
    paper_id: string;
    paper_title: string;
    paper_doi?: string;
    paper_url?: string;
    code_url?: string;
    code_source: string;
    task_match: string;
    input_type: string;
    labels_supported: string[];
    dataset_used?: string;
    metrics_reported: string[];
    reproducibility_score: number;
    license?: string;
    run_command?: string;
    verified_repo: boolean;
    reproduction_status: string;
    risks: string[];
    repo_type?: string;
    is_model_baseline?: boolean;
    matches_task_domain?: boolean;
    baseline_priority_score?: number;
    baseline_rejection_reason?: string | null;
    stars?: number;
  }>;
  novelty_report?: {
    similar_work: Array<Record<string, string>>;
    has_public_code: boolean;
    overlap_points: string[];
    retainable_novelty: string[];
    claims_to_downgrade: string[];
    optimization_directions: string[];
  };
  arena_result?: {
    arena_id: string;
    mode: string;
    arena_level: string;
    candidates: Array<{
      hypothesis_id: string;
      statement: string;
      is_user_idea: boolean;
      weighted_score: number;
      rank: number;
      critic_scores?: Record<string, {
        novelty: number; self_consistency: number; verifiability: number;
        data_availability: number; feasibility: number; evidence_support: number;
        reproducibility: number; competition_fit: number; risk: string; revision_advice: string;
      }>;
    }>;
    ranking: string[];
    selected_for_experiment: string;
    switchback_candidate?: string | null;
    ablation_design: Array<{ challenge_id: string; tests_innovation_point: string; expected_insight: string; derivation_from_main: string }>;
  };
  constraints: {
    must_verify_citations: boolean;
    max_papers: number;
    require_experiment_plan: boolean;
    enable_browser_worker: boolean;
    enable_semantic_scholar: boolean;
    enable_arxiv: boolean;
    workflow_mode: "auto" | "guided";
  };
  status: string;
  control_action: "none" | "pause" | "abandon";
  pause_reason: "user" | "review" | "error" | null;
  current_stage: string;
  progress: number;
  workspace_path?: string;
  workspace_artifacts: Record<string, string>;
  evidence_frozen: boolean;
  citation_frozen: boolean;
  frozen_evidence_ids: string[];
  frozen_paper_ids: string[];
  plan: Record<string, unknown>;
  perspectives: Array<{
    perspective: string;
    role: string;
    question: string;
    search_query: string;
    evidence_requirement: string;
    risk_control: string;
  }>;
  steps: Array<{
    name: string;
    status: string;
    summary: string;
    attempts?: number;
    error_code?: string | null;
    error_summary?: string | null;
    retryable?: boolean;
    skippable?: boolean;
    events?: Array<{ event: string; at: string; detail: string }>;
  }>;
  papers: Array<{
    paper_id: string;
    title: string;
    authors: string[];
    year?: number;
    publication_date?: string;
    doi?: string;
    openalex_id?: string;
    source_api?: string;
    semantic_scholar_id?: string;
    arxiv_id?: string;
    source_url?: string;
    pdf_url?: string;
    code_url?: string;
    abstract: string;
    venue?: string;
    work_type?: string;
    cited_by_count?: number;
    fields_of_study: string[];
    is_open_access?: boolean;
    is_retracted: boolean;
    verification_status: string;
    title_match_score?: number;
    verification_method?: string;
    verification_confidence?: number;
    matched_source?: string;
    report_eligible: boolean;
    human_decision: "pending" | "accepted" | "rejected";
    human_note: string;
    frozen: boolean;
    paper_role?: string;
    seismic_relevant?: boolean;
    baseline_eligible?: boolean;
    baseline_rejection_reason?: string | null;
  }>;
  paper_chunks: Array<{
    chunk_id: string;
    paper_id?: string;
    source_title: string;
    source_path?: string;
    source_url?: string;
    page?: number;
    section?: string;
    text: string;
    token_estimate: number;
  }>;
  evidence: Array<{
    evidence_id: string;
    claim: string;
    evidence_type: string;
    source_title: string;
    source_path?: string;
    source_url?: string;
    page?: number;
    section?: string;
    verified: boolean;
    quote_or_summary: string;
    verification_method?: string;
    verification_confidence?: number;
    matched_source?: string;
    eligible_for_report: boolean;
    human_decision: "pending" | "accepted" | "rejected";
    human_note: string;
    frozen: boolean;
  }>;
  knowledge_cards: Array<{
    card_id: string;
    title: string;
    perspective: string;
    finding: string;
    method: string;
    dataset: string;
    limitation: string;
    transferability: string;
    evidence_ids: string[];
    paper_ids: string[];
    confidence: number;
    report_eligible: boolean;
  }>;
  citation_report?: {
    total: number;
    verified: number;
    suspicious: number;
    hallucinated: number;
    skipped: number;
    integrity_score: number;
  };
  claim_audit?: {
    total: number;
    supported: number;
    weakly_supported: number;
    unsupported: number;
    support_score: number;
    items: Array<{
      claim_id: string;
      claim: string;
      status: string;
      confidence: number;
      matched_evidence_ids: string[];
      reason: string;
    }>;
  };
  data_profiles: DatasetProfile[];
  baseline_result_card?: BaselineResultCard;
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
      feasibility: number;
      evidence_support: number;
      reproducibility: number;
      competition_fit: number;
      risk: string;
      revision_advice: string;
    };
    reviewer_comments: Array<{
      reviewer: string;
      score: number;
      stance: string;
      comment: string;
      required_action: string;
    }>;
    revision_history: Array<{
      before: string;
      after: string;
      rationale: string;
      changed_by: string;
    }>;
    selection_rationale: string;
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
    english_report?: FormalReport;
    chinese_report?: FormalReport;
    system_provenance?: {
      agent_workflow: Array<Record<string, unknown>>;
      evidence_ledger: Array<Record<string, unknown>>;
      citation_audit_log: string[];
      claim_audit_summary: Record<string, unknown>;
      run_metadata: Record<string, unknown>;
    };
    paper_title: string;
    problem_statement: string;
    rationale: string;
    methods: string[];
    knowledge_cards: Array<{
      card_id: string;
      finding: string;
      perspective: string;
      evidence_ids: string[];
    }>;
    results: string;
    baseline_result_card?: {
      name: string;
      metrics: Record<string, number>;
      result_summary: string;
    };
    citation_audit_log: string[];
  };
  code_experiment?: CodeExperimentResult | null;
  experiment_assistance?: ExperimentAssistanceInput | null;
  result_evaluation?: ResultEvaluation | null;
  ablation_analysis?: AblationAnalysis | null;
  result_interpretation?: ResultInterpretation | null;
  novelty_verdict?: NoveltyVerdict | null;
  novelty_status?: "not_checked" | "ok" | "low_novelty";
  novelty_round?: number;
  baseline_gate_status?: BaselineGateStatus | null;
  re_search_round?: number;
  evidence_changed?: boolean;
  hypothesis_changed?: boolean;
  baseline_changed?: boolean;
  experiment_redesign_round?: number;
  macro_round?: number;
  switchback_used?: boolean;
  code_experiment_mode?: string | null;
  errors: string[];
  resume_count?: number;
  trust_warnings?: string[];
  last_action?: Record<string, unknown> | null;
};

export type FormalReport = {
  paper_title: string;
  paper_abstract: string;
  problem_statement: string;
  rationale: string;
  technical_details: string;
  datasets: {
    source: string;
    target: string;
  };
  methods: string;
  experiments: {
    baselines: string;
    metrics: string;
    design: string;
  };
  results: {
    executed_results: string;
    expected_validation_outcomes: string;
  };
  limitations_and_risk_controls: string;
  references: Array<{
    paper_id: string;
    title: string;
    authors: string[];
    year?: number;
    doi?: string;
    openalex_id?: string;
    arxiv_id?: string;
    source_url?: string;
    verification_status: string;
    verification_method?: string;
    verification_confidence?: number;
    report_eligible: boolean;
  }>;
};

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    }
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function createRun(
  question: string,
  domain: string,
  maxPapers: number,
  enableSemanticScholar: boolean,
  enableArxiv: boolean,
  workflowMode: "auto" | "guided" = "auto",
  mode: "discovery" | "idea_refinement" | "experiment_assistance" = "discovery"
) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs`, {
    method: "POST",
    body: JSON.stringify({
      domain,
      question,
      mode,
      constraints: {
        must_verify_citations: true,
        max_papers: maxPapers,
        require_experiment_plan: true,
        enable_browser_worker: false,
        enable_semantic_scholar: enableSemanticScholar,
        enable_arxiv: enableArxiv,
        workflow_mode: workflowMode
      }
    })
  });
}

export async function startRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/start`, { method: "POST" });
}

export async function attachExperimentAssistance(runId: string, payload: ExperimentAssistanceInput) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/experiment-assistance`, {
    method: "POST", body: JSON.stringify(payload)
  });
}

export async function attachBaselineIntake(runId: string, payload: BaselineIntakeRequest) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/baseline-intake`, {
    method: "POST", body: JSON.stringify(payload)
  });
}

export async function continueRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/continue`, { method: "POST" });
}

export async function actOnRunStep(runId: string, stepName: string, action: RunStepAction) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/steps/${stepName}/action`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export async function recoverRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/recover`, { method: "POST" });
}

export async function pauseRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/pause`, { method: "POST" });
}

export async function resumeRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/resume`, { method: "POST" });
}

export async function abandonRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/abandon`, { method: "POST" });
}

export async function getRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}`);
}

export async function listRuns() {
  return requestJson<ResearchRun[]>(`${API_BASE}/api/runs`);
}

export async function listRestorableWorkspaces() {
  return requestJson<RestorableWorkspace[]>(`${API_BASE}/api/runs/workspaces`);
}

export async function restoreWorkspace(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/workspace/restore`, { method: "POST" });
}

export async function getPublicConfig() {
  return requestJson<PublicConfig>(`${API_BASE}/api/system/config`);
}

export async function getDataProfiles() {
  return requestJson<DatasetProfile[]>(`${API_BASE}/api/data/profiles`);
}

export async function runBaseline() {
  return requestJson<BaselineResultCard>(`${API_BASE}/api/data/baseline`, { method: "POST" });
}

export async function captureBrowserPage(url: string) {
  return requestJson<BrowserCaptureResult>(`${API_BASE}/api/browser/capture`, {
    method: "POST",
    body: JSON.stringify({ url, download_pdfs: true, max_pdf_downloads: 3 })
  });
}

export async function previewPaper(paperId: string, sourceUrl: string) {
  return requestJson<PaperPreviewResult>(`${API_BASE}/api/browser/paper-preview`, {
    method: "POST",
    body: JSON.stringify({ paper_id: paperId, source_url: sourceUrl }),
  });
}

export async function ingestPdfEvidence(runId: string, pdfPath: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/pdf-evidence`, {
    method: "POST",
    body: JSON.stringify({ pdf_path: pdfPath })
  });
}

export async function decideEvidence(
  runId: string,
  evidenceId: string,
  decision: "pending" | "accepted" | "rejected",
  note = ""
) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/evidence/${evidenceId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, note })
  });
}

export async function freezeEvidence(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/evidence/freeze`, { method: "POST" });
}

export async function unfreezeEvidence(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/evidence/unfreeze`, { method: "POST" });
}

export async function decidePaper(
  runId: string,
  paperId: string,
  decision: "pending" | "accepted" | "rejected",
  note = ""
) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/papers/${paperId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, note })
  });
}

export async function freezePapers(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/papers/freeze`, { method: "POST" });
}

export async function unfreezePapers(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/papers/unfreeze`, { method: "POST" });
}

export async function rebuildReport(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/report/rebuild`, { method: "POST" });
}

export async function selectHypothesis(runId: string, hypothesisId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/hypotheses/${hypothesisId}/select`, {
    method: "POST"
  });
}

export async function discoverBaselines(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/baselines/discover`, { method: "POST" });
}

export async function verifyBaselineRepo(runId: string, baselineId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/baselines/${baselineId}/verify-repo`, { method: "POST" });
}

export function reportExportUrl(runId: string, format: "md" | "json" | "pdf" = "md") {
  return `${API_BASE}/api/runs/${runId}/report/export?format=${format}`;
}

export function workspaceExportUrl(runId: string) {
  return `${API_BASE}/api/runs/${runId}/workspace/export`;
}
