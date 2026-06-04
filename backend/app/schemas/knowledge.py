from pydantic import BaseModel, Field


class KnowledgeCard(BaseModel):
    card_id: str
    title: str
    perspective: str = "literature"
    finding: str
    method: str = ""
    dataset: str = ""
    limitation: str = ""
    transferability: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.6
    report_eligible: bool = False
