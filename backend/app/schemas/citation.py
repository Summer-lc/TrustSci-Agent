from pydantic import BaseModel, Field


class CitationVerificationResult(BaseModel):
    paper_id: str
    title: str
    status: str
    confidence: float = 0.0
    method: str
    details: str = ""
    matched_source: str | None = None
    doi: str | None = None
    source_api: str = "unknown"


class CitationVerificationReport(BaseModel):
    total: int = 0
    verified: int = 0
    suspicious: int = 0
    hallucinated: int = 0
    skipped: int = 0
    integrity_score: float = 1.0
    results: list[CitationVerificationResult] = Field(default_factory=list)
