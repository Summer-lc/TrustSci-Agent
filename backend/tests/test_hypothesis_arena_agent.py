import pytest

from app.agents.hypothesis_arena_agent import HypothesisArenaAgent, ARENA_WEIGHTS
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import Hypothesis


class StubHypothesisAgent:
    async def arun(self, gaps, evidence, data_profiles, *, run_id, avoid_prior_art=None):
        return [Hypothesis(hypothesis_id="H1", statement="s1", rationale="r", novelty_claim="n", verification_path="v"),
                Hypothesis(hypothesis_id="H2", statement="s2", rationale="r", novelty_claim="n", verification_path="v"),
                Hypothesis(hypothesis_id="H3", statement="s3", rationale="r", novelty_claim="n", verification_path="v")]


class StubCriticArena:
    async def arun(self, hypotheses, evidence, *, run_id):
        # H1 scores high, H3 second, H2 low
        from app.schemas.hypothesis import CriticReview
        high = CriticReview(novelty=9, self_consistency=9, verifiability=9, data_availability=9, feasibility=9,
                            evidence_support=9, reproducibility=9, competition_fit=9, risk="r", revision_advice="a")
        low = CriticReview(novelty=5, self_consistency=5, verifiability=5, data_availability=5, feasibility=5,
                           evidence_support=5, reproducibility=5, competition_fit=5, risk="r", revision_advice="a")
        mid = CriticReview(novelty=7, self_consistency=7, verifiability=7, data_availability=7, feasibility=7,
                           evidence_support=7, reproducibility=7, competition_fit=7, risk="r", revision_advice="a")
        per = {"domain_scientist": {"H1": high, "H2": low, "H3": mid},
               "ml_critic": {"H1": high, "H2": low, "H3": mid},
               "skeptical_reviewer": {"H1": high, "H2": low, "H3": mid}}
        return per


class StubRevision:
    def run(self, hypotheses):
        for h in hypotheses:
            h.revised_statement = h.statement + " (revised)"
        return hypotheses


@pytest.mark.asyncio
async def test_discovery_arena_ranks_and_selects_top1() -> None:
    agent = HypothesisArenaAgent(hypothesis_agent=StubHypothesisAgent(), critic_arena=StubCriticArena(), revision=StubRevision())
    result, hypotheses = await agent.arun("discovery", gaps=[], evidence=[], data_profiles=[], idea_brief=None, papers=[], run_id="run_x")
    assert result.mode == "discovery"
    assert result.ranking[0] == "H1"  # highest weighted score
    assert result.selected_for_experiment == "H1"
    assert result.switchback_candidate == "H3"  # second rank
    selected = [h for h in hypotheses if h.selected]
    assert len(selected) == 1 and selected[0].hypothesis_id == "H1"


@pytest.mark.asyncio
async def test_arena_weighted_score_is_normalized_0_to_100() -> None:
    from app.schemas.hypothesis import CriticReview
    perfect = CriticReview(novelty=10, self_consistency=10, verifiability=10, data_availability=10, feasibility=10,
                           evidence_support=10, reproducibility=10, competition_fit=10, risk="r", revision_advice="a")
    scores = {p: {"H1": perfect} for p in ("domain_scientist", "ml_critic", "skeptical_reviewer")}
    score = HypothesisArenaAgent(hypothesis_agent=StubHypothesisAgent(), critic_arena=StubCriticArena(), revision=StubRevision())._weighted_score(scores, "H1")
    assert 99.0 <= score <= 100.0
