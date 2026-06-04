from pydantic import BaseModel, Field

from app.schemas.data import BaselineResultCard, DatasetProfile
from app.schemas.experiment import ExperimentPlan
from app.schemas.knowledge import KnowledgeCard
from app.schemas.paper import Paper


class ResearchReport(BaseModel):
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
