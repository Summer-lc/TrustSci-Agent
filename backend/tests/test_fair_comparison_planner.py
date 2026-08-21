from app.agents.fair_comparison_planner import FairComparisonPlanner
from app.schemas.code_experiment import FairComparisonPlan


def test_plan_shape_and_defaults() -> None:
    p = FairComparisonPlanner().plan()
    assert isinstance(p, FairComparisonPlan)
    assert p.method_name == "SeismicModel"
    assert p.baseline_source == "harness_trivial"
    assert p.split_strategy == "event_level"
    assert "accuracy" in p.metrics and "macro_f1" in p.metrics
    assert "no leakage" in p.preprocessing


def test_plan_respects_baseline_source() -> None:
    p = FairComparisonPlanner().plan(baseline_source="verified_repo")
    assert p.baseline_source == "verified_repo"
