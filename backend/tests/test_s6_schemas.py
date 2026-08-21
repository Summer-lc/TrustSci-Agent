import math

import pytest
from pydantic import ValidationError

from app.schemas.experiment_assistance import ExperimentAssistanceInput, MetricObservation, ResultEvaluation
from app.schemas.run import ResearchConstraints, ResearchRun


def test_assistance_requires_metric_or_log() -> None:
    with pytest.raises(ValidationError):
        ExperimentAssistanceInput(objective="Compare classifiers", method_summary="FFT model")


def test_metric_rejects_non_finite_values() -> None:
    with pytest.raises(ValidationError):
        MetricObservation(name="accuracy", value=math.inf)


def test_assistance_round_trip_on_run() -> None:
    supplied = ExperimentAssistanceInput(
        objective="Evaluate event classification", method_summary="FFT random forest",
        baseline_metrics=[MetricObservation(name="accuracy", value=0.8)],
        method_metrics=[MetricObservation(name="accuracy", value=0.86)],
    )
    run = ResearchRun(domain="seismic_event_classification", question="q", mode="experiment_assistance",
                      constraints=ResearchConstraints(), experiment_assistance=supplied,
                      result_evaluation=ResultEvaluation(verdict="pass"))
    restored = ResearchRun.model_validate_json(run.model_dump_json())
    assert restored.experiment_assistance.method_metrics[0].value == 0.86
    assert restored.result_evaluation.verdict == "pass"
