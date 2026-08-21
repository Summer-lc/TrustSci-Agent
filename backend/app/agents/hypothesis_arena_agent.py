from app.agents.critic_arena_agent import CriticArenaAgent, PERSPECTIVES
from app.agents.hypothesis_agent import HypothesisAgent
from app.agents.revision_agent import RevisionAgent
from app.schemas.arena import AblationChallenge, HypothesisArenaCandidate, HypothesisArenaResult
from app.schemas.evidence import EvidenceItem
from app.schemas.hypothesis import CriticReview, Hypothesis

ARENA_WEIGHTS = {
    "novelty": 1.5, "verifiability": 1.5, "reproducibility": 1.3, "evidence_support": 1.3,
    "feasibility": 1.2, "data_availability": 1.2, "competition_fit": 1.0, "self_consistency": 1.0,
}
_DIMS = ("novelty", "self_consistency", "verifiability", "data_availability", "feasibility",
         "evidence_support", "reproducibility", "competition_fit")
_WEIGHT_SUM = sum(ARENA_WEIGHTS.values())


class HypothesisArenaAgent:
    """v3 Hypothesis Arena: Discovery ranking or Idea Refinement ablation.

    Discovery: generate N -> 3 parallel critics -> weighted rank -> Top1/Top2 -> revision -> auto-select Top1.
    Idea Refinement: H_main + 3 challengers -> critics -> ablation_design -> select H_main.
    No human gate (auto-select).
    """

    def __init__(self, *, hypothesis_agent: HypothesisAgent, critic_arena: CriticArenaAgent,
                 revision: RevisionAgent, challenger=None) -> None:
        self.hypothesis_agent = hypothesis_agent
        self.critic_arena = critic_arena
        self.revision = revision
        self.challenger = challenger

    async def arun(self, mode, gaps, evidence: list[EvidenceItem], data_profiles, idea_brief, papers, *, run_id: str, avoid_prior_art: list[str] | None = None) -> tuple[HypothesisArenaResult, list[Hypothesis]]:
        if mode == "idea_refinement":
            return await self._idea_refinement(evidence, idea_brief, run_id)
        return await self._discovery(gaps, evidence, data_profiles, run_id, avoid_prior_art=avoid_prior_art)

    async def _discovery(self, gaps, evidence, data_profiles, run_id, *, avoid_prior_art: list[str] | None = None) -> tuple[HypothesisArenaResult, list[Hypothesis]]:
        hypotheses = await self.hypothesis_agent.arun(gaps, evidence, data_profiles, run_id=run_id, avoid_prior_art=avoid_prior_art)
        scores = await self.critic_arena.arun(hypotheses, evidence, run_id=run_id)
        ranked = self._rank(hypotheses, scores)
        top1, top2 = ranked[0], (ranked[1] if len(ranked) > 1 else None)
        # Revise top candidates only (cost control).
        self.revision.run([top1] + ([top2] if top2 else []))
        for h in hypotheses:
            h.selected = (h.hypothesis_id == top1.hypothesis_id)
        candidates = self._candidates(hypotheses, scores, ranked)
        result = HypothesisArenaResult(
            arena_id=f"arena_{run_id[:12]}", mode="discovery", arena_level="simplified_ranking",
            candidates=candidates, ranking=[c.hypothesis_id for c in candidates],
            selected_for_experiment=top1.hypothesis_id,
            switchback_candidate=top2.hypothesis_id if top2 else None, ablation_design=[],
        )
        return result, hypotheses

    async def _idea_refinement(self, evidence, idea_brief, run_id) -> tuple[HypothesisArenaResult, list[Hypothesis]]:
        h_main = self._h_main_from_idea(idea_brief)
        challengers: list[Hypothesis] = []
        ablation: list[AblationChallenge] = []
        if self.challenger is not None and idea_brief is not None:
            challengers, ablation = await self.challenger.arun(h_main, idea_brief, run_id=run_id)
        all_hyps = [h_main] + challengers
        scores = await self.critic_arena.arun(all_hyps, evidence, run_id=run_id)
        ranked = self._rank(all_hyps, scores)
        self.revision.run([h_main])
        for h in all_hyps:
            h.selected = (h.hypothesis_id == h_main.hypothesis_id)
        candidates = self._candidates(all_hyps, scores, ranked)
        # mark which is the user idea
        for c in candidates:
            c.is_user_idea = (c.hypothesis_id == h_main.hypothesis_id)
        result = HypothesisArenaResult(
            arena_id=f"arena_{run_id[:12]}", mode="idea_refinement", arena_level="simplified_ranking",
            candidates=candidates, ranking=[c.hypothesis_id for c in candidates],
            selected_for_experiment=h_main.hypothesis_id, switchback_candidate=None,
            ablation_design=ablation,
        )
        return result, all_hyps

    def _h_main_from_idea(self, idea_brief) -> Hypothesis:
        if idea_brief is None:
            return Hypothesis(hypothesis_id="H_main", statement="user idea", rationale="no idea brief",
                              novelty_claim="user-provided", verification_path="to be defined")
        return Hypothesis(
            hypothesis_id="H_main",
            statement=idea_brief.user_idea or idea_brief.research_problem,
            rationale=f"User-provided idea for {idea_brief.target_task}",
            novelty_claim=idea_brief.expected_contribution or "user idea to be validated",
            verification_path="Validate via bounded experiment against ablation challengers.",
        )

    def _rank(self, hypotheses: list[Hypothesis], scores: dict) -> list[Hypothesis]:
        return sorted(hypotheses, key=lambda h: self._weighted_score(scores, h.hypothesis_id), reverse=True)

    def _weighted_score(self, scores: dict, hypothesis_id: str) -> float:
        # Average across perspectives of weighted sum of dims, scaled to 0..100.
        per_perspective: list[float] = []
        for perspective in PERSPECTIVES:
            review: CriticReview | None = scores.get(perspective, {}).get(hypothesis_id)
            if review is None:
                continue
            weighted = sum(getattr(review, dim) * ARENA_WEIGHTS[dim] for dim in _DIMS)
            per_perspective.append(weighted / _WEIGHT_SUM)  # 1..10
        if not per_perspective:
            return 0.0
        avg = sum(per_perspective) / len(per_perspective)  # 1..10
        return round(avg * 10.0, 2)  # 10..100

    def _candidates(self, hypotheses: list[Hypothesis], scores: dict, ranked: list[Hypothesis]) -> list[HypothesisArenaCandidate]:
        rank_index = {h.hypothesis_id: i + 1 for i, h in enumerate(ranked)}
        out: list[HypothesisArenaCandidate] = []
        for h in ranked:
            critic_scores = {p: scores.get(p, {}).get(h.hypothesis_id) for p in PERSPECTIVES
                             if scores.get(p, {}).get(h.hypothesis_id) is not None}
            out.append(HypothesisArenaCandidate(
                hypothesis_id=h.hypothesis_id, statement=h.revised_statement or h.statement,
                is_user_idea=False, critic_scores=critic_scores,
                weighted_score=self._weighted_score(scores, h.hypothesis_id), rank=rank_index[h.hypothesis_id],
            ))
        return out
