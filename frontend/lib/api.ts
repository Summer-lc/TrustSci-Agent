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
  links: Array<Record<string, string>>;
  pdf_links: Array<Record<string, string>>;
  downloaded_pdfs: Array<Record<string, string | number>>;
};

export type ResearchRun = {
  run_id: string;
  domain: string;
  question: string;
  constraints: {
    must_verify_citations: boolean;
    max_papers: number;
    require_experiment_plan: boolean;
    enable_browser_worker: boolean;
    enable_semantic_scholar: boolean;
    enable_arxiv: boolean;
  };
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
    source_api?: string;
    semantic_scholar_id?: string;
    arxiv_id?: string;
    verification_status: string;
    title_match_score?: number;
    verification_method?: string;
    verification_confidence?: number;
    matched_source?: string;
    report_eligible: boolean;
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
  enableArxiv: boolean
) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs`, {
    method: "POST",
    body: JSON.stringify({
      domain,
      question,
      constraints: {
        must_verify_citations: true,
        max_papers: maxPapers,
        require_experiment_plan: true,
        enable_browser_worker: false,
        enable_semantic_scholar: enableSemanticScholar,
        enable_arxiv: enableArxiv
      }
    })
  });
}

export async function startRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/start`, { method: "POST" });
}

export async function getRun(runId: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}`);
}

export async function listRuns() {
  return requestJson<ResearchRun[]>(`${API_BASE}/api/runs`);
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

export async function ingestPdfEvidence(runId: string, pdfPath: string) {
  return requestJson<ResearchRun>(`${API_BASE}/api/runs/${runId}/pdf-evidence`, {
    method: "POST",
    body: JSON.stringify({ pdf_path: pdfPath })
  });
}

export function reportExportUrl(runId: string, format: "md" | "json" = "md") {
  return `${API_BASE}/api/runs/${runId}/report/export?format=${format}`;
}
