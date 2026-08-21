import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


async def _noop(self, run): return None


@pytest.mark.asyncio
async def test_classic_seismic_runs_new_steps_linearly(monkeypatch, tmp_path):
    wf = ScientistWorkflow(Settings(dashscope_api_key="", max_papers=2))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    for m in ("_plan", "_search_literature", "_verify_citations", "_build_evidence",
              "_mine_literature", "_classify_papers", "_profile_scientific_data", "_run_arena",
              "_run_novelty_check", "_run_baseline_intake", "_evaluate_baseline_gate", "_design_experiment",
              "_run_code_experiment", "_evaluate_experiment_result_gate", "_redesign_experiment",
              "_run_macro_react", "_write_report", "_verify_claims",
              "_revise_report_after_audit", "_translate_report", "_route_intent"):
        monkeypatch.setattr(ScientistWorkflow, m, _noop, raising=False)
    monkeypatch.setattr(wf.literature_router, "search", _noop)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf._run_after_evidence_review(run)
    names = [s.name for s in run.steps if s.status == "completed"]
    # new steps present in order, no loop back
    assert "novelty_check" in names and names.index("novelty_check") > names.index("arena")
    assert "baseline_intake" in names and names.index("baseline_intake") > names.index("novelty_check")
    assert "baseline_quality_gate" in names and names.index("baseline_quality_gate") > names.index("baseline_intake")
    assert "baseline_verify" not in names
    assert "baseline_discover" not in names
    # no re_search loop in classic single-pass
    assert "re_search_literature" not in names
