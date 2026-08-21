from pydantic import BaseModel, Field


class BaselineCandidate(BaseModel):
    baseline_id: str
    paper_id: str
    paper_title: str
    paper_doi: str | None = None
    paper_url: str | None = None
    code_url: str | None = None
    code_source: str  # github_search | paperswithcode | user_provided
    task_match: str
    input_type: str  # waveform | spectrogram | multi_channel_waveform | unknown
    labels_supported: list[str] = Field(default_factory=list)
    dataset_used: str | None = None
    metrics_reported: list[str] = Field(default_factory=list)
    reproducibility_score: float = 0.0  # 0..1, filled by RepositoryVerifier
    license: str | None = None
    run_command: str | None = None
    verified_repo: bool = False
    reproduction_status: str = "pending"  # pending | verified | suspicious | failed
    risks: list[str] = Field(default_factory=list)
    repo_type: str = "unknown"  # model_code | dataset_only | benchmark_suite | docs_only | unknown
    is_model_baseline: bool = False
    matches_task_domain: bool = False
    baseline_priority_score: float = 0.0
    baseline_rejection_reason: str | None = None
    stars: int = 0
