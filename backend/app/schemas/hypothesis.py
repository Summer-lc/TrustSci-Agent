from pydantic import BaseModel, Field


class CriticReview(BaseModel):
    novelty: int
    self_consistency: int
    verifiability: int
    data_availability: int
    feasibility: int = 8
    evidence_support: int = 7
    reproducibility: int = 8
    competition_fit: int = 8
    risk: str
    revision_advice: str


class ReviewerComment(BaseModel):
    reviewer: str
    score: int
    stance: str
    comment: str
    required_action: str


class RevisionRecord(BaseModel):
    before: str
    after: str
    rationale: str
    changed_by: str = "RevisionAgent"


class Hypothesis(BaseModel):
    hypothesis_id: str
    statement: str
    rationale: str
    supporting_evidence: list[str] = Field(default_factory=list)
    novelty_claim: str
    verification_path: str
    critic: CriticReview | None = None
    reviewer_comments: list[ReviewerComment] = Field(default_factory=list)
    revised_statement: str | None = None
    revision_history: list[RevisionRecord] = Field(default_factory=list)
    selected: bool = False
    selection_rationale: str = ""
