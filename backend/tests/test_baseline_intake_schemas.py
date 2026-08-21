import pytest
from pydantic import ValidationError

from app.schemas.baseline_intake import (
    BaselineIntake,
    BaselineIntakeRequest,
    ManualBaselineInput,
    MetricObservation,
)
from app.schemas.run import ResearchConstraints, ResearchRun


def test_manual_baseline_request_accepts_metrics() -> None:
    payload = BaselineIntakeRequest(
        strategy="manual_upload",
        manual=ManualBaselineInput(
            name="User RF baseline",
            description="RandomForest baseline from prior experiment.",
            dataset_description="Synthetic seismic demo split.",
            metrics=[MetricObservation(name="accuracy", value=0.81, split="test")],
            repository_url="https://example.com/baseline",
            run_command="python train_baseline.py",
            notes="Provided by user before run.",
        ),
    )
    assert payload.strategy == "manual_upload"
    assert payload.manual is not None
    assert payload.manual.metrics[0].value == 0.81


def test_manual_baseline_requires_useful_content() -> None:
    with pytest.raises(ValidationError):
        BaselineIntakeRequest(
            strategy="manual_upload",
            manual=ManualBaselineInput(name="b"),
        )


def test_ai_generated_and_none_do_not_require_manual_payload() -> None:
    assert BaselineIntakeRequest(strategy="ai_generated").manual is None
    assert BaselineIntakeRequest(strategy="none").manual is None


def test_metric_rejects_non_finite_value() -> None:
    with pytest.raises(ValidationError):
        MetricObservation(name="accuracy", value=float("nan"))


def test_research_run_round_trips_baseline_fields() -> None:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        baseline_strategy="manual_upload",
        baseline_intake=BaselineIntake(
            strategy="manual_upload",
            source_type="manual_upload",
            trust_level="user_provided",
            name="User baseline",
            description="Provided baseline.",
            metrics=[MetricObservation(name="accuracy", value=0.8)],
            limitations=[],
            provenance_notes=["attached before start"],
        ),
    )
    restored = ResearchRun.model_validate_json(run.model_dump_json())
    assert restored.baseline_strategy == "manual_upload"
    assert restored.baseline_intake is not None
    assert restored.baseline_intake.name == "User baseline"
