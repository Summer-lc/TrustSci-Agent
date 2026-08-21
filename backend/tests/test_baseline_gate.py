from app.workflows.scientist_workflow import _baseline_gate_status
from app.schemas.baseline import BaselineCandidate


def _c(**kw) -> BaselineCandidate:
    base = dict(baseline_id="b", paper_id="p", paper_title="t", code_url="https://github.com/a/b",
                code_source="github_search", task_match="seismic", input_type="waveform", stars=10)
    base.update(kw)
    return BaselineCandidate(**base)


def test_gate_research_grade_with_one_verified() -> None:
    cands = [_c(verified_repo=True, is_model_baseline=True, matches_task_domain=True,
                repo_type="model_code", reproducibility_score=0.8,
                reproduction_status="verified")]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is True
    assert g.comparison_grade == "research"
    assert g.external_verified_model_baselines == 1
    assert g.comparable_count == 2  # 1 verified + harness_trivial


def test_gate_requires_consistent_verified_model_baseline() -> None:
    cands = [_c(verified_repo=True, is_model_baseline=True, matches_task_domain=True,
                repo_type="model_code", reproducibility_score=0.8,
                reproduction_status="suspicious")]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert g.comparison_grade == "degraded"
    assert g.external_verified_model_baselines == 0


def test_gate_degraded_when_zero_verified() -> None:
    cands = [_c(verified_repo=False, is_model_baseline=True, matches_task_domain=True,
                repo_type="model_code", reproducibility_score=0.5)]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert g.comparison_grade == "degraded"
    assert "no verified external model baseline" in g.insufficient_reasons


def test_gate_flags_dataset_only_candidates() -> None:
    cands = [_c(verified_repo=False, is_model_baseline=False, repo_type="dataset_only")]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert any("dataset" in r or "docs" in r or "empty" in r for r in g.insufficient_reasons)


def test_gate_flags_task_mismatch() -> None:
    cands = [_c(verified_repo=False, is_model_baseline=True, matches_task_domain=False,
                repo_type="model_code", reproducibility_score=0.8)]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert any("task" in r for r in g.insufficient_reasons)


def test_gate_flags_low_repro() -> None:
    cands = [_c(verified_repo=False, is_model_baseline=True, matches_task_domain=True,
                repo_type="model_code", reproducibility_score=0.4)]
    g = _baseline_gate_status(cands)
    assert g.research_gate_passed is False
    assert any("reproducibility" in r.lower() for r in g.insufficient_reasons)
