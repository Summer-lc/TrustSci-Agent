from app.agents.revision_agent import RevisionAgent
from app.schemas.feedback_loop import NoveltyVerdict
from app.schemas.hypothesis import Hypothesis


def test_revision_applies_claim_revision_to_top1() -> None:
    h = Hypothesis(hypothesis_id="H1", statement="original claim", rationale="r",
                   novelty_claim="n", verification_path="v", selected=True)
    verdict = NoveltyVerdict(verdict="similar_work",
                             claim_revision="narrowed claim: verifiable improvement path")
    RevisionAgent().run([h], novelty_verdict=verdict)
    assert h.revised_statement == "narrowed claim: verifiable improvement path"
    assert h.revision_history
    assert h.revision_history[-1].before == "original claim"
    assert h.revision_history[-1].after == "narrowed claim: verifiable improvement path"
    assert "novelty" in h.revision_history[-1].rationale.lower()


def test_revision_keeps_suffix_when_no_novelty() -> None:
    h = Hypothesis(hypothesis_id="H1", statement="original claim", rationale="r",
                   novelty_claim="n", verification_path="v", selected=True)
    RevisionAgent().run([h], novelty_verdict=None)
    # original deterministic suffix path
    assert h.revised_statement is not None
    assert "bounded" in h.revised_statement.lower() or h.revised_statement != h.statement
