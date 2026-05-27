from app.schemas.hypothesis import Hypothesis


class HypothesisAgent:
    def run(self, gaps: list[dict]) -> list[Hypothesis]:
        evidence_ids = gaps[0].get("evidence", []) if gaps else []
        return [
            Hypothesis(
                hypothesis_id="H1",
                statement="Combining literature-derived mechanism features with structure-property descriptors can improve prioritization of solid-state electrolyte candidates under stability constraints.",
                rationale="The hypothesis joins two evidence streams: verified papers describing transport/stability mechanisms and open datasets that support measurable property prediction.",
                supporting_evidence=evidence_ids,
                novelty_claim="The novelty is not a new material claim, but a traceable hypothesis workflow that connects mechanism text, database features, and explicit validation metrics.",
                verification_path="Build composition-only and structure-aware baselines, add literature-derived mechanism tags, and compare ranking and regression metrics.",
            ),
            Hypothesis(
                hypothesis_id="H2",
                statement="A citation-verified evidence ledger can reduce unsupported assumptions in early-stage energy-materials ideation while preserving enough diversity for expert review.",
                rationale="Current deep research systems often optimize answer synthesis; competition requirements demand stricter provenance for every key claim.",
                supporting_evidence=evidence_ids,
                novelty_claim="The claim focuses on trustworthy AI Scientist process design rather than unbounded autonomous discovery.",
                verification_path="Compare reports generated with and without citation freezing, then audit unsupported claims and rejected references.",
            ),
            Hypothesis(
                hypothesis_id="H3",
                statement="Human-in-the-loop critic scoring can select more verifiable hypotheses than single-pass generation for materials discovery questions.",
                rationale="Multi-agent debate exposes risks around novelty overlap, data availability, and metric mismatch before the final report is written.",
                supporting_evidence=evidence_ids,
                novelty_claim="The process explicitly optimizes for contest evaluation dimensions: novelty, self-consistency, verifiability, and reproducibility.",
                verification_path="Score candidate hypotheses before and after critic revision, then track accepted revisions and evidence coverage.",
            ),
        ]

