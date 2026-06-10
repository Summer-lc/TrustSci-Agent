from typing import Literal

from pydantic import BaseModel, Field


class Paper(BaseModel):
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    publication_date: str | None = None
    doi: str | None = None
    openalex_id: str | None = None
    semantic_scholar_id: str | None = None
    arxiv_id: str | None = None
    source_url: str | None = None
    pdf_url: str | None = None
    abstract: str = ""
    venue: str | None = None
    work_type: str | None = None
    cited_by_count: int | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    is_open_access: bool | None = None
    is_retracted: bool = False
    source_api: str = "unknown"
    verified_by: list[str] = Field(default_factory=list)
    verification_status: str = "unverified"
    title_match_score: float | None = None
    verification_method: str | None = None
    verification_confidence: float | None = None
    matched_source: str | None = None
    report_eligible: bool = False
    human_decision: Literal["pending", "accepted", "rejected"] = "pending"
    human_note: str = ""
    frozen: bool = False


class PaperDecisionRequest(BaseModel):
    decision: Literal["pending", "accepted", "rejected"]
    note: str = ""
