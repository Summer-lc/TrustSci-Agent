from app.schemas.baseline import BaselineCandidate
from app.schemas.paper import Paper
from app.schemas.run import ResearchConstraints, ResearchRun


def test_paper_baseline_role_fields_default() -> None:
    p = Paper(paper_id="p1", title="t")
    assert p.paper_role == "unknown"
    assert p.seismic_relevant is False
    assert p.baseline_eligible is False
    assert p.baseline_rejection_reason is None
    assert p.code_url_source is None


def test_baseline_candidate_quality_fields_default() -> None:
    c = BaselineCandidate(baseline_id="b1", paper_id="p1", paper_title="t",
                          code_url="https://github.com/a/b", code_source="github_search",
                          task_match="seismic", input_type="waveform")
    assert c.repo_type == "unknown"
    assert c.is_model_baseline is False
    assert c.matches_task_domain is False
    assert c.baseline_priority_score == 0.0
    assert c.baseline_rejection_reason is None
    assert c.stars == 0


def test_code_url_extractor_records_source(tmp_path, monkeypatch) -> None:
    from app.tools.code_url_extractor import extract_code_urls
    p = Paper(paper_id="p1", title="t", abstract="see https://github.com/foo/bar for code", pdf_url=None)
    out = extract_code_urls([p])
    assert out[0].code_url == "https://github.com/foo/bar"
    assert out[0].code_url_source == "abstract"
