from typing import Literal

from pydantic import BaseModel, Field


class PaperChunk(BaseModel):
    chunk_id: str
    paper_id: str | None = None
    source_title: str = ""
    source_path: str | None = None
    source_url: str | None = None
    page: int | None = None
    section: str | None = None
    text: str
    token_estimate: int = 0


class EvidenceItem(BaseModel):
    evidence_id: str
    paper_id: str | None = None
    claim: str
    evidence_type: str = "paper"
    source_title: str = ""
    source_url: str | None = None
    source_path: str | None = None
    doi: str | None = None
    page: int | None = None
    section: str | None = None
    quote_or_summary: str
    confidence: float = 0.7
    verified: bool = False
    verification_method: str | None = None
    verification_confidence: float | None = None
    matched_source: str | None = None
    eligible_for_report: bool = False
    human_decision: Literal["pending", "accepted", "rejected"] = "pending"
    human_note: str = ""
    frozen: bool = False
    tags: list[str] = Field(default_factory=list)


class EvidenceLedger(BaseModel):
    items: list[EvidenceItem] = Field(default_factory=list)


class PdfEvidenceIngestRequest(BaseModel):
    pdf_path: str
    paper_id: str | None = None
    source_title: str = ""
    source_url: str | None = None
    max_pages: int = Field(default=6, ge=1, le=20)


class EvidenceDecisionRequest(BaseModel):
    decision: Literal["pending", "accepted", "rejected"]
    note: str = ""
