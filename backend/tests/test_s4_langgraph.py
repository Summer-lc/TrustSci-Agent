# backend/tests/test_s4_langgraph.py
import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.langgraph_workflow import LangGraphWorkflow


async def _noop_step(self, run) -> None:
    """Stub for heavy step methods. Bound via class-level monkeypatch so
    `self` is passed (instance-attribute functions would NOT bind self)."""
    return None


_STEP_METHODS = (
    "_plan", "_search_literature_with_langchain_tools",
    "_verify_citations_with_langchain_tools", "_build_evidence",
    "_mine_literature", "_classify_papers", "_profile_scientific_data",
    "_run_arena", "_run_baseline_intake", "_design_experiment", "_run_code_experiment",
    "_run_novelty_check", "_evaluate_baseline_gate", "_re_search_literature",
    "_run_macro_react", "_evaluate_experiment_result_gate", "_redesign_experiment",
    "_evaluate_results", "_analyze_ablations", "_interpret_results",
    "_generate_and_critique", "_write_report", "_verify_claims",
    "_revise_report_after_audit", "_translate_report", "_route_intent",
)


def _stub_steps(monkeypatch) -> None:
    for m in _STEP_METHODS:
        monkeypatch.setattr(LangGraphWorkflow, m, _noop_step)


def _completed_names(run: ResearchRun) -> list[str]:
    return [s.name for s in run.steps if s.status == "completed"]


@pytest.mark.asyncio
async def test_seismic_run_inserts_code_experiment_between_experiment_design_and_report(monkeypatch):
    _stub_steps(monkeypatch)
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    result = await wf.run(run)
    names = _completed_names(result)
    assert "code_experiment" in names
    assert names.index("code_experiment") > names.index("experiment_design")
    assert names.index("code_experiment") < names.index("report_writer")
    assert "baseline_intake" in names
    assert "baseline_discover" not in names
    assert "baseline_verify" not in names
    assert names.index("baseline_intake") > names.index("novelty_check")
    assert names.index("baseline_quality_gate") > names.index("baseline_intake")
    assert names.index("result_evaluation") < names.index("report_writer")
    # seismic path runs arena, not hypothesis_debate
    assert "arena" in names
    assert "hypothesis_debate" not in names


@pytest.mark.asyncio
async def test_non_seismic_run_traverses_code_experiment_as_noop(monkeypatch):
    _stub_steps(monkeypatch)
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    run = ResearchRun(domain="energy_materials", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    result = await wf.run(run)
    names = _completed_names(result)
    # code_experiment is in the linear path (no-op for non-seismic), per the
    # paper_classification pattern — so the non-seismic step_names assertion in
    # test_langgraph_workflow_completes_sync_run must include it too.
    assert "code_experiment" in names
    assert names.index("code_experiment") > names.index("experiment_design")
    assert names.index("code_experiment") < names.index("report_writer")
    # non-seismic runs hypothesis_debate, not arena
    assert "hypothesis_debate" in names
    assert "arena" not in names
