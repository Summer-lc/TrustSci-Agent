from copy import deepcopy

from app.schemas.experiment import ExperimentPlan
from app.schemas.run import ResearchRun


class ExperimentRedesignAgent:
    async def arun(self, run: ResearchRun) -> ExperimentPlan:
        base = deepcopy(run.experiment_plan)
        if base is None:
            return ExperimentPlan(
                datasets=["synthetic seismic demo"],
                source="waveform",
                target="event_class",
                baselines=["selected baseline strategy"],
                metrics=["accuracy", "macro_f1"],
                experiment_steps=[
                    "Redesign rationale: previous experiment plan was missing, so use a conservative waveform baseline comparison.",
                    "Extract time-domain and spectral summary features before model training.",
                    "Evaluate on the fixed event-level test split and compare against the harness baseline.",
                ],
                expected_results="The redesigned experiment should expose whether feature changes improve robustness.",
                failure_modes=["No improvement after redesign", "Synthetic split is too easy or too small"],
            )
        notes = []
        if run.code_experiment and run.code_experiment.comparison.notes:
            notes = run.code_experiment.comparison.notes
        rationale = "Redesign rationale: previous executable result underperformed the selected baseline."
        if notes:
            rationale += f" Last comparison note: {notes[0]}"
        base.experiment_steps = [
            rationale,
            "Add or emphasize spectral and time-domain feature checks before fitting the classifier.",
            "Re-run the same fixed split so the redesigned result remains comparable.",
        ] + list(base.experiment_steps)
        if "macro_f1" not in base.metrics:
            base.metrics.append("macro_f1")
        base.expected_results = (
            "The redesigned experiment should recover performance or provide a clearer negative result "
            "with documented limitations."
        )
        if "Redesign still fails to beat baseline" not in base.failure_modes:
            base.failure_modes.append("Redesign still fails to beat baseline")
        return base
