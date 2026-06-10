from app.schemas.hypothesis import CriticReview, Hypothesis, ReviewerComment


class CriticAgent:
    def run(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        reviewed: list[Hypothesis] = []
        for hypothesis in hypotheses:
            hypothesis.critic = CriticReview(
                novelty=8 if hypothesis.hypothesis_id == "H1" else 7,
                self_consistency=8,
                verifiability=9,
                data_availability=8,
                feasibility=8,
                evidence_support=7 if hypothesis.supporting_evidence else 5,
                reproducibility=8,
                competition_fit=9,
                risk="Novelty may overlap with existing materials informatics workflows unless the evidence-ledger contribution is made explicit.",
                revision_advice="Freeze verified references before report writing and add one bounded benchmark or dataset profile to support the validation path.",
            )
            hypothesis.reviewer_comments = _reviewer_comments(hypothesis)
            reviewed.append(hypothesis)
        return reviewed


def _reviewer_comments(hypothesis: Hypothesis) -> list[ReviewerComment]:
    evidence_note = (
        "supporting evidence ids are present"
        if hypothesis.supporting_evidence
        else "supporting evidence is currently sparse"
    )
    return [
        ReviewerComment(
            reviewer="Literature Reviewer",
            score=7,
            stance="cautious_support",
            comment=f"The idea is plausible, but novelty should be bounded because {evidence_note}.",
            required_action="Add a similar-work boundary and cite only verified papers.",
        ),
        ReviewerComment(
            reviewer="Domain Scientist",
            score=8,
            stance="support",
            comment="The statement is scientifically useful if it remains framed as a testable mechanism or workflow hypothesis.",
            required_action="Name the measurable material property and avoid claiming discovery before validation.",
        ),
        ReviewerComment(
            reviewer="ML/Experiment Reviewer",
            score=8,
            stance="support_with_conditions",
            comment="The validation path is feasible if baseline, metrics, and ablation are explicit.",
            required_action="Tie the experiment plan to a concrete dataset profile and baseline result card.",
        ),
        ReviewerComment(
            reviewer="Skeptical Reviewer",
            score=6,
            stance="major_revision",
            comment="The final report could overstate novelty if the evidence-ledger contribution is not separated from materials-science claims.",
            required_action="Revise the claim to separate verified evidence from expected outcomes.",
        ),
    ]
