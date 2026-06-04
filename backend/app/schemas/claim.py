from pydantic import BaseModel, Field


class ClaimAuditItem(BaseModel):
    claim_id: str
    claim: str
    status: str
    confidence: float = 0.0
    matched_evidence_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class ClaimAuditReport(BaseModel):
    total: int = 0
    supported: int = 0
    weakly_supported: int = 0
    unsupported: int = 0
    support_score: float = 0.0
    items: list[ClaimAuditItem] = Field(default_factory=list)
