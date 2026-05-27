from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    evidence_id: str
    paper_id: str | None = None
    claim: str
    evidence_type: str = "paper"
    source_title: str = ""
    source_url: str | None = None
    doi: str | None = None
    page: int | None = None
    quote_or_summary: str
    confidence: float = 0.7
    verified: bool = False
    tags: list[str] = Field(default_factory=list)


class EvidenceLedger(BaseModel):
    items: list[EvidenceItem] = Field(default_factory=list)

