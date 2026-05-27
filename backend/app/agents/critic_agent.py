from app.schemas.hypothesis import CriticReview, Hypothesis


class CriticAgent:
    def run(self, hypotheses: list[Hypothesis]) -> list[Hypothesis]:
        reviewed: list[Hypothesis] = []
        for hypothesis in hypotheses:
            hypothesis.critic = CriticReview(
                novelty=8 if hypothesis.hypothesis_id == "H1" else 7,
                self_consistency=8,
                verifiability=9,
                data_availability=8,
                risk="Novelty may overlap with existing materials informatics workflows unless the evidence-ledger contribution is made explicit.",
                revision_advice="Freeze verified references before report writing and add one bounded benchmark or dataset profile to support the validation path.",
            )
            hypothesis.revised_statement = (
                hypothesis.statement
                + " The final claim must be treated as a testable research plan, not as an already-proven discovery."
            )
            reviewed.append(hypothesis)
        return reviewed

