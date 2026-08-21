from typing import Any

from pydantic import BaseModel, Field

from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.experiment import ExperimentPlan
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper


class ReportDatasets(BaseModel):
    source: str
    target: str


class ReportExperiments(BaseModel):
    baselines: str
    metrics: str
    design: str


class ReportResults(BaseModel):
    executed_results: str
    expected_validation_outcomes: str


class FormalResearchReport(BaseModel):
    paper_title: str
    paper_abstract: str
    problem_statement: str
    rationale: str
    technical_details: str
    datasets: ReportDatasets
    methods: str
    experiments: ReportExperiments
    results: ReportResults
    limitations_and_risk_controls: str
    references: list[Paper] = Field(default_factory=list)


class SystemProvenance(BaseModel):
    agent_workflow: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ledger: list[dict[str, Any]] = Field(default_factory=list)
    citation_audit_log: list[str] = Field(default_factory=list)
    claim_audit_summary: dict[str, Any] = Field(default_factory=dict)
    run_metadata: dict[str, Any] = Field(default_factory=dict)
    arena_report: dict[str, Any] = Field(default_factory=dict)
    baseline_provenance: dict[str, Any] = Field(default_factory=dict)
    experiment_iteration_log: list[dict[str, Any]] = Field(default_factory=list)
    code_debug_log: list[dict[str, Any]] = Field(default_factory=list)
    ablation_report: dict[str, Any] = Field(default_factory=dict)
    result_support_judgment: dict[str, Any] = Field(default_factory=dict)


class ResearchReport(BaseModel):
    english_report: FormalResearchReport | None = None
    chinese_report: FormalResearchReport | None = None
    system_provenance: SystemProvenance | None = None
    problem_statement: str
    rationale: str
    technical_details: list[str]
    datasets: list[str]
    source: str
    target: str
    paper_title: str
    paper_abstract: str
    methods: list[str]
    experiments: ExperimentPlan
    results: str
    data_profiles: list[DatasetProfile] = Field(default_factory=list)
    baseline_result_card: BaselineResultCard | None = None
    knowledge_cards: list[KnowledgeCard] = Field(default_factory=list)
    references: list[Paper] = Field(default_factory=list)
    citation_audit_log: list[str] = Field(default_factory=list)
