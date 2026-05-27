from pydantic import BaseModel, Field


class Paper(BaseModel):
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    source_url: str | None = None
    abstract: str = ""
    venue: str | None = None
    verified_by: list[str] = Field(default_factory=list)
    verification_status: str = "unverified"
    title_match_score: float | None = None

