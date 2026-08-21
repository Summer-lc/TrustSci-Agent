import pytest

from app.agents.experiment_redesign_agent import ExperimentRedesignAgent
from app.config import Settings
from app.schemas.code_experiment import CodeExperimentResult, ComparisonResult, ExperimentSummary
from app.schemas.experiment import ExperimentPlan
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


def _run_with_negative_result() -> ResearchRun:
    run = ResearchRun(
        domain="seismic_event_classification",
        question="q",
        constraints=ResearchConstraints(),
        experiment_plan=ExperimentPlan(
            datasets=["synthetic seismic demo"],
            source="waveform",
            target="event_class",
            baselines=["harness baseline"],
            metrics=["accuracy"],
            experiment_steps=["train initial model"],
            expected_results="Beat baseline.",
            failure_modes=["overfitting"],
        ),
    )
    run.code_experiment = CodeExperimentResult(
        comparison=ComparisonResult(
            baseline_metrics={"accuracy": 0.90},
            method_metrics={"accuracy": 0.70},
            method_beats_baseline=False,
            outcome="completed_negative",
            notes=["method underperformed"],
        ),
        summary=ExperimentSummary(
            outcome="completed_negative",
            tests_pass=True,
            method_beats_baseline=False,
            best_metric=0.70,
        ),
    )
    return run


@pytest.mark.asyncio
async def test_redesign_agent_adds_rationale_and_new_step() -> None:
    run = _run_with_negative_result()
    plan = await ExperimentRedesignAgent().arun(run)
    assert "Redesign rationale" in plan.experiment_steps[0]
    assert plan.expected_results
    assert len(plan.experiment_steps) >= len(run.experiment_plan.experiment_steps)


def test_result_gate_routes_completed_negative_to_redesign() -> None:
    workflow = ScientistWorkflow(Settings())
    run = _run_with_negative_result()
    route = workflow._route_after_experiment_result({"run": run})
    assert route == "experiment_redesign"


def test_redesign_cap_routes_to_result_evaluation() -> None:
    workflow = ScientistWorkflow(Settings())
    run = _run_with_negative_result()
    run.experiment_redesign_round = 1
    route = workflow._route_after_experiment_result({"run": run})
    assert route == "result_evaluation"


@pytest.mark.asyncio
async def test_experiment_redesign_updates_plan_and_counter() -> None:
    workflow = ScientistWorkflow(Settings())
    run = _run_with_negative_result()
    await workflow._redesign_experiment(run)
    assert run.experiment_redesign_round == 1
    assert "Redesign rationale" in run.experiment_plan.experiment_steps[0]
