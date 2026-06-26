from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.claim import ClaimAuditReport
from app.schemas.common import AgentStep, RunStatus, utc_now
from app.schemas.citation import CitationVerificationReport
from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.evidence import EvidenceItem, PaperChunk
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper
from app.schemas.planner import PerspectiveQuestion
from app.schemas.report import ResearchReport


class ResearchConstraints(BaseModel):
    must_verify_citations: bool = True
    max_papers: int = 6
    require_experiment_plan: bool = True
    enable_browser_worker: bool = False
    enable_semantic_scholar: bool = False
    enable_arxiv: bool = True
    workflow_mode: Literal["auto", "guided"] = "auto"


class ResearchRunCreate(BaseModel):
    domain: str = "energy_materials"
    question: str
    constraints: ResearchConstraints = Field(default_factory=ResearchConstraints)


class ResearchRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run_{uuid4().hex[:10]}")
    domain: str
    question: str
    constraints: ResearchConstraints
    status: RunStatus = RunStatus.created
    current_stage: str = "created"
    progress: float = 0
    workspace_path: str | None = None
    workspace_artifacts: dict[str, str] = Field(default_factory=dict)
    created_at: Any = Field(default_factory=utc_now)
    updated_at: Any = Field(default_factory=utc_now)
    plan: dict[str, Any] = Field(default_factory=dict)
    perspectives: list[PerspectiveQuestion] = Field(default_factory=list)
    steps: list[AgentStep] = Field(default_factory=list)
    papers: list[Paper] = Field(default_factory=list)
    citation_report: CitationVerificationReport | None = None
    paper_chunks: list[PaperChunk] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_frozen: bool = False
    citation_frozen: bool = False
    frozen_evidence_ids: list[str] = Field(default_factory=list)
    frozen_paper_ids: list[str] = Field(default_factory=list)
    knowledge_cards: list[KnowledgeCard] = Field(default_factory=list)
    claim_audit: ClaimAuditReport | None = None
    data_profiles: list[DatasetProfile] = Field(default_factory=list)
    baseline_result_card: BaselineResultCard | None = None
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    experiment_plan: ExperimentPlan | None = None
    report: ResearchReport | None = None
    errors: list[str] = Field(default_factory=list)
