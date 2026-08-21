from app.schemas.feedback_loop import NoveltyVerdict, BaselineGateStatus
from app.schemas.code_experiment import CodeExperimentResult
from app.schemas.run import ResearchRun, ResearchConstraints


def test_novelty_verdict_defaults() -> None:
    v = NoveltyVerdict()
    assert v.verdict == "novel"
    assert v.claim_revision is None
    assert v.prior_art_paper_ids == []
    assert v.reasoning == ""


def test_baseline_gate_status_defaults() -> None:
    g = BaselineGateStatus()
    assert g.external_verified_model_baselines == 0
    assert g.comparable_count == 1  # harness_trivial
    assert g.run_gate_passed is True
    assert g.research_gate_passed is False
    assert g.comparison_grade == "degraded"


def test_code_experiment_trigger_default() -> None:
    ce = CodeExperimentResult()
    assert ce.trigger == "initial"


def test_run_s5_fields_default() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints())
    assert run.novelty_verdict is None
    assert run.novelty_status == "not_checked"
    assert run.novelty_round == 0
    assert run.baseline_gate_status is None
    assert run.re_search_round == 0
    assert run.evidence_changed is False
    assert run.hypothesis_changed is False
    assert run.baseline_changed is False
    assert run.macro_round == 0
    assert run.switchback_used is False
    assert run.code_experiment_mode is None
