from app.config import Settings
from app.schemas.code_experiment import (
    CodeExperimentResult, AcceptanceGate, ComparisonResult, FairComparisonPlan,
    IterEntry, DebugEntry, ExperimentSummary,
)
from app.schemas.run import ResearchRun, ResearchConstraints


def test_code_experiment_result_defaults() -> None:
    r = CodeExperimentResult()
    assert r.harness_version == "seismic_sklearn_v1"
    assert r.model_family == "sklearn"
    assert r.baseline_source == "harness_trivial"
    assert r.model_py_source == ""
    assert isinstance(r.fair_comparison_plan, FairComparisonPlan)
    assert isinstance(r.acceptance_gate, AcceptanceGate)
    assert isinstance(r.comparison, ComparisonResult)
    assert r.iteration_log == [] and r.debug_log == []
    assert isinstance(r.summary, ExperimentSummary)


def test_acceptance_gate_all_passed() -> None:
    g = AcceptanceGate()
    assert g.all_passed is False
    g2 = AcceptanceGate(tests_pass=True, metrics_generated=True, baseline_comparison_written=True)
    assert g2.all_passed is True


def test_comparison_outcome_literal() -> None:
    c = ComparisonResult(outcome="completed_positive", method_beats_baseline=True)
    assert c.outcome == "completed_positive"
    c2 = ComparisonResult()
    assert c2.outcome == "failed"  # default
    assert c2.method_beats_baseline is False


def test_experiment_summary_structured() -> None:
    s = ExperimentSummary()
    assert s.outcome == "failed"
    assert s.tests_pass is False
    assert s.method_beats_baseline is False
    assert s.baseline_source == "harness_trivial"
    assert s.best_metric is None
    assert s.failure_reason is None


def test_run_has_code_experiment_field() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints())
    assert run.code_experiment is None


def test_settings_experiments_dir_and_timeout() -> None:
    s = Settings(dashscope_api_key="")
    assert s.experiments_dir.parts[-2:] == ("experiments", "seismic_event_classification")
    assert s.code_experiment_timeout_seconds == 120
