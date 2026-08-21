# backend/tests/test_macro_react.py
import pytest

from app.config import Settings
from app.schemas.code_experiment import CodeExperimentResult, ComparisonResult, ExperimentSummary
from app.schemas.hypothesis import Hypothesis
from app.schemas.run import ResearchConstraints, ResearchRun
from app.schemas.arena import HypothesisArenaResult
from app.workflows.scientist_workflow import ScientistWorkflow


def _ce(outcome, method_acc=0.4, baseline_acc=0.9) -> CodeExperimentResult:
    return CodeExperimentResult(
        trigger="initial",
        comparison=ComparisonResult(outcome=outcome, method_beats_baseline=(method_acc > baseline_acc),
                                    method_metrics={"accuracy": method_acc},
                                    baseline_metrics={"accuracy": baseline_acc}),
        summary=ExperimentSummary(outcome=outcome, method_beats_baseline=(method_acc > baseline_acc),
                                   best_metric=method_acc, tests_pass=True),
    )


def _run_with_code_exp(ce, switchback_id=None):
    r = ResearchRun(domain="seismic_event_classification", question="q",
                    constraints=ResearchConstraints(), mode="discovery")
    r.code_experiment = ce
    r.arena_result = HypothesisArenaResult(arena_id="a", mode="discovery",
                                           arena_level="simplified_ranking", candidates=[],
                                           ranking=[], selected_for_experiment="H1",
                                           switchback_candidate=switchback_id, ablation_design=[])
    return r


def _wf():
    return ScientistWorkflow(Settings(dashscope_api_key="", max_papers=2))


@pytest.mark.asyncio
async def test_macro_positive_accepted_no_macro():
    wf = _wf()
    r = _run_with_code_exp(_ce("completed_positive", 0.9, 0.5))
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None  # accept, no escalation
    assert r.macro_round == 0


@pytest.mark.asyncio
async def test_macro_failed_triggers_macro_round_1():
    wf = _wf()
    r = _run_with_code_exp(_ce("failed"))
    await wf._run_macro_react(r)
    assert r.code_experiment_mode == "macro"
    assert r.macro_round == 1


@pytest.mark.asyncio
async def test_macro_big_margin_negative_triggers_macro():
    wf = _wf()
    r = _run_with_code_exp(_ce("completed_negative", method_acc=0.3, baseline_acc=0.9))  # margin 0.6
    await wf._run_macro_react(r)
    assert r.code_experiment_mode == "macro"
    assert r.macro_round == 1


@pytest.mark.asyncio
async def test_macro_narrow_negative_accepted():
    wf = _wf()
    r = _run_with_code_exp(_ce("completed_negative", method_acc=0.86, baseline_acc=0.9))  # margin 0.04 < 0.05
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None  # narrow negative (<0.05) accepted, no macro


@pytest.mark.asyncio
async def test_macro_after_cap_switchback_to_top2():
    wf = _wf()
    r = _run_with_code_exp(_ce("failed"), switchback_id="H2")
    r.macro_round = 1  # macro already used
    r.hypotheses = [
        Hypothesis(hypothesis_id="H1", statement="s1", rationale="r1", novelty_claim="n1", verification_path="v1", selected=True),
        Hypothesis(hypothesis_id="H2", statement="s2", rationale="r2", novelty_claim="n2", verification_path="v2"),
    ]
    await wf._run_macro_react(r)
    assert r.code_experiment_mode == "switchback"
    assert r.switchback_used is True


@pytest.mark.asyncio
async def test_macro_no_top2_accepts_negative():
    wf = _wf()
    r = _run_with_code_exp(_ce("failed"), switchback_id=None)
    r.macro_round = 1
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None  # accept negative, no further escalation


@pytest.mark.asyncio
async def test_macro_stale_switchback_candidate_accepts_negative():
    wf = _wf()
    r = _run_with_code_exp(_ce("failed"), switchback_id="H_STALE")
    r.macro_round = 1
    r.hypotheses = [
        Hypothesis(hypothesis_id="H1", statement="s1", rationale="r1", novelty_claim="n1", verification_path="v1", selected=True),
        Hypothesis(hypothesis_id="H2", statement="s2", rationale="r2", novelty_claim="n2", verification_path="v2"),
    ]
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None  # stale ID → fall through, accept negative
    assert r.switchback_used is False


@pytest.mark.asyncio
async def test_macro_non_seismic_noop():
    wf = _wf()
    r = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    await wf._run_macro_react(r)
    assert r.code_experiment_mode is None
    assert r.macro_round == 0
