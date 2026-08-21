from app.schemas.arena import AblationChallenge, HypothesisArenaCandidate, HypothesisArenaResult
from app.schemas.hypothesis import CriticReview
from app.schemas.run import ResearchConstraints, ResearchRun


def _review(score: int = 8) -> CriticReview:
    return CriticReview(novelty=score, self_consistency=score, verifiability=score,
                        data_availability=score, feasibility=score, evidence_support=score,
                        reproducibility=score, competition_fit=score, risk="r", revision_advice="a")


def test_arena_candidate_defaults() -> None:
    c = HypothesisArenaCandidate(hypothesis_id="H1", statement="s", is_user_idea=False,
                                 critic_scores={"domain_scientist": _review()}, weighted_score=80.0, rank=1)
    assert c.rank == 1
    assert c.critic_scores["domain_scientist"].novelty == 8


def test_arena_result_defaults() -> None:
    r = HypothesisArenaResult(arena_id="a1", mode="discovery", arena_level="simplified_ranking",
                              candidates=[], ranking=[], selected_for_experiment="",
                              switchback_candidate=None, ablation_design=[])
    assert r.arena_level == "simplified_ranking"
    assert r.switchback_candidate is None


def test_research_run_arena_field() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints())
    assert run.arena_result is None


def test_ablation_challenge() -> None:
    a = AblationChallenge(challenge_id="H_c1", tests_innovation_point="spectrogram branch",
                          expected_insight="verify fusion > waveform-only", derivation_from_main="remove spectrogram")
    assert a.tests_innovation_point == "spectrogram branch"
