from __future__ import annotations

from app.schemas.feedback_loop import NoveltyVerdict
from app.schemas.hypothesis import Hypothesis, RevisionRecord


class RevisionAgent:
    """Deterministic hypothesis reviser for the MVP debate loop + S5 feedback loop."""

    def run(self, hypotheses: list[Hypothesis], novelty_verdict: NoveltyVerdict | None = None) -> list[Hypothesis]:
        for hypothesis in hypotheses:
            if novelty_verdict and novelty_verdict.claim_revision and hypothesis.selected:
                before = hypothesis.revised_statement or hypothesis.statement
                after = novelty_verdict.claim_revision
                if after != before:
                    hypothesis.revised_statement = after
                    hypothesis.revision_history.append(RevisionRecord(
                        before=before,
                        after=after,
                        rationale=f"novelty verdict: {novelty_verdict.verdict} — claim narrowed",
                    ))
                continue
            # original deterministic suffix path
            after = _revised_statement(hypothesis)
            if after != hypothesis.statement:
                hypothesis.revised_statement = after
                hypothesis.revision_history.append(
                    RevisionRecord(
                        before=hypothesis.statement,
                        after=after,
                        rationale=_revision_rationale(hypothesis),
                    )
                )
        return hypotheses


def _revised_statement(hypothesis: Hypothesis) -> str:
    suffix = (
        " This should be evaluated as a bounded, evidence-linked research plan with explicit baselines, "
        "not as an already-proven materials discovery."
    )
    if hypothesis.statement.endswith(suffix.strip()):
        return hypothesis.statement
    return hypothesis.statement.rstrip(".") + "." + suffix


def _revision_rationale(hypothesis: Hypothesis) -> str:
    actions = [comment.required_action for comment in hypothesis.reviewer_comments[:3]]
    if not actions and hypothesis.critic:
        actions = [hypothesis.critic.revision_advice]
    return "Revision applies reviewer constraints: " + "; ".join(actions or ["keep claims bounded and verifiable"])
