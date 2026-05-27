from pydantic import BaseModel, Field


class CriticReview(BaseModel):
    novelty: int
    self_consistency: int
    verifiability: int
    data_availability: int
    risk: str
    revision_advice: str


class Hypothesis(BaseModel):
    hypothesis_id: str
    statement: str
    rationale: str
    supporting_evidence: list[str] = Field(default_factory=list)
    novelty_claim: str
    verification_path: str
    critic: CriticReview | None = None
    revised_statement: str | None = None
    selected: bool = False

