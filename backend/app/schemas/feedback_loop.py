from typing import Literal

from pydantic import BaseModel, Field


class NoveltyVerdict(BaseModel):
    verdict: Literal["novel", "transfer_applicability", "already_done",
                     "dataset_only", "similar_work"] = "novel"
    claim_revision: str | None = None
    prior_art_paper_ids: list[str] = Field(default_factory=list)
    overlap_points: list[str] = Field(default_factory=list)
    retainable_novelty: list[str] = Field(default_factory=list)
    reasoning: str = ""
    # backward-compat with the old novelty_report dict fields
    similar_work: list[dict] = Field(default_factory=list)
    has_public_code: bool = False


class BaselineGateStatus(BaseModel):
    external_verified_model_baselines: int = 0
    comparable_count: int = 1  # harness_trivial always counts as 1
    run_gate_passed: bool = True
    research_gate_passed: bool = False
    insufficient_reasons: list[str] = Field(default_factory=list)
    comparison_grade: Literal["research", "degraded"] = "degraded"
