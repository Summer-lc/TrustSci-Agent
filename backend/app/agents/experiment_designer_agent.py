from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.data import DatasetProfile


class ExperimentDesignerAgent:
    def run(self, selected: Hypothesis | None, data_profiles: list[DatasetProfile] | None = None) -> ExperimentPlan:
        target = selected.statement if selected else "Validate the selected AI-generated materials hypothesis."
        datasets = [profile.name for profile in data_profiles or []] or [
            "Matbench-like open materials property table",
            "Materials Project-derived candidate metadata",
            "User-uploaded CSV for sample profiling",
        ]
        return ExperimentPlan(
            datasets=datasets,
            source="Verified literature metadata, paper abstracts/full text where available, and public materials datasets.",
            target="A bounded candidate set with composition, structure descriptors, stability indicators, and target property labels.",
            baselines=[
                "composition-only regression/ranking baseline",
                "structure-descriptor baseline",
                "literature-augmented feature baseline",
            ],
            metrics=["MAE", "R2", "top-k hit rate", "evidence coverage", "unsupported-claim count"],
            experiment_steps=[
                "Create a clean candidate table and profile missing values.",
                "Train or simulate the composition-only baseline.",
                "Add structure descriptors and compare predictive metrics.",
                "Add literature-derived mechanism tags linked to evidence IDs.",
                "Run ablation and generate a result card for the final report.",
            ],
            expected_results=f"The plan should show whether this hypothesis is feasible to test: {target}",
            failure_modes=["Insufficient labels", "feature leakage", "weak novelty against prior structure-aware models"],
        )
