from pydantic import BaseModel, Field

from app.schemas.hypothesis import CriticReview


class HypothesisArenaCandidate(BaseModel):
    hypothesis_id: str
    statement: str
    is_user_idea: bool = False
    critic_scores: dict[str, CriticReview] = Field(default_factory=dict)
    weighted_score: float = 0.0
    rank: int = 0


class AblationChallenge(BaseModel):
    challenge_id: str
    tests_innovation_point: str
    expected_insight: str
    derivation_from_main: str


class HypothesisArenaResult(BaseModel):
    arena_id: str
    mode: str  # discovery | idea_refinement
    arena_level: str = "simplified_ranking"  # elo_tournament deferred to S7
    candidates: list[HypothesisArenaCandidate] = Field(default_factory=list)
    ranking: list[str] = Field(default_factory=list)  # hypothesis_id by rank
    selected_for_experiment: str = ""
    switchback_candidate: str | None = None
    ablation_design: list[AblationChallenge] = Field(default_factory=list)
    # Elo upgrade fields (S7) — reserved, unused in S3:
    pairwise_results: list[dict] | None = None
    evolution_history: list[dict] | None = None
