from app.schemas.baseline import BaselineCandidate
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


def test_baseline_candidate_defaults() -> None:
    bc = BaselineCandidate(
        baseline_id="baseline_001",
        paper_id="paper_001",
        paper_title="Deep seismic event classification",
        code_url="https://github.com/example/seismic-cnn",
        code_source="github_search",
        task_match="seismic event classification",
        input_type="waveform",
    )
    assert bc.reproducibility_score == 0.0
    assert bc.verified_repo is False
    assert bc.reproduction_status == "pending"
    assert bc.risks == []
    assert bc.run_command is None


def test_paper_has_code_url() -> None:
    p = Paper(paper_id="p1", title="t", code_url="https://github.com/x/y")
    assert p.code_url == "https://github.com/x/y"


def test_research_run_baseline_fields_default_empty() -> None:
    run = ResearchRun(domain="seismic_event_classification", question="q", constraints=ResearchConstraints())
    assert run.baseline_candidates == []
    assert run.novelty_report is None
