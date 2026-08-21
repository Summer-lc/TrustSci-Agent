"""Deterministic fair-comparison planner (no LLM).

Fairness is mechanical, not a judgment call: same event-level split, same
metrics, same preprocessing for method and baseline. Only the method (model.py)
varies. This object is surfaced to the report + CodePlanPanel so the fairness
contract is explicit rather than implicit."""
from app.schemas.code_experiment import FairComparisonPlan


class FairComparisonPlanner:
    def plan(self, *, baseline_source: str = "harness_trivial") -> FairComparisonPlan:
        return FairComparisonPlan(
            method_name="SeismicModel",
            baseline_source=baseline_source,
            split_strategy="event_level",
            metrics=["accuracy", "macro_f1"],
            preprocessing="raw waveform, fixed event-level train/val/test split, "
                          "same preprocessing for method and baseline, no leakage",
        )
