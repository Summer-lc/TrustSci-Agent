import pytest

from app.config import Settings
from app.schemas.run import ResearchConstraints, ResearchRun
from app.schemas.feedback_loop import NoveltyVerdict
from app.workflows.langgraph_workflow import LangGraphWorkflow


async def _noop_step(self, run): return None


def _stub(monkeypatch, methods):
    for m in methods:
        monkeypatch.setattr(LangGraphWorkflow, m, _noop_step)


@pytest.mark.asyncio
async def test_novelty_already_done_routes_back_to_arena_under_cap(monkeypatch):
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    _stub(monkeypatch, ["_plan", "_search_literature_with_langchain_tools",
        "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
        "_classify_papers", "_profile_scientific_data", "_run_baseline_intake",
        "_evaluate_baseline_gate", "_design_experiment", "_run_code_experiment",
        "_evaluate_experiment_result_gate", "_redesign_experiment", "_run_macro_react", "_write_report",
        "_verify_claims", "_revise_report_after_audit", "_translate_report", "_route_intent"])
    # _run_arena + _run_novelty_check are real-ish (stubbed to set state):
    async def fake_arena(self, run):
        run.arena_result = None  # minimal
        run.novelty_round = getattr(run, "novelty_round", 0)
    async def fake_novelty(self, run):
        run.novelty_verdict = NoveltyVerdict(verdict="already_done", prior_art_paper_ids=["p1"])
        run.novelty_round += 1
    monkeypatch.setattr(LangGraphWorkflow, "_run_arena", fake_arena)
    monkeypatch.setattr(LangGraphWorkflow, "_run_novelty_check", fake_novelty)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf.run(run)
    # novelty_round incremented (at least one already_done → regen attempted)
    assert run.novelty_round >= 1
    # cap enforced: novelty_round <= 2
    assert run.novelty_round <= 2
    names = [s.name for s in run.steps if s.status == "completed"]
    assert "novelty_check" in names
    assert names.index("novelty_check") > names.index("arena")


@pytest.mark.asyncio
async def test_baseline_gate_degraded_after_cap_routes_to_experiment_design(monkeypatch):
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    _stub(monkeypatch, ["_plan", "_search_literature_with_langchain_tools",
        "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
        "_classify_papers", "_profile_scientific_data", "_run_arena", "_run_novelty_check",
        "_run_baseline_intake", "_design_experiment", "_run_code_experiment",
        "_evaluate_experiment_result_gate", "_redesign_experiment", "_run_macro_react", "_write_report",
        "_verify_claims", "_revise_report_after_audit", "_translate_report", "_route_intent"])
    async def fake_gate(self, run):
        from app.schemas.feedback_loop import BaselineGateStatus
        run.baseline_gate_status = BaselineGateStatus(research_gate_passed=False, comparison_grade="degraded")
        run.re_search_round = 2  # cap reached
    monkeypatch.setattr(LangGraphWorkflow, "_evaluate_baseline_gate", fake_gate)
    async def fake_research(self, run): raise AssertionError("should not re-search at cap")
    monkeypatch.setattr(LangGraphWorkflow, "_re_search_literature", fake_research)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf.run(run)
    names = [s.name for s in run.steps if s.status == "completed"]
    assert "baseline_quality_gate" in names
    assert "baseline_intake" in names
    assert "baseline_discover" not in names
    assert "baseline_verify" not in names
    assert "experiment_design" in names
    # re_search NOT in steps (cap reached, degraded -> experiment_design)
    assert "re_search_literature" not in names


@pytest.mark.asyncio
async def test_research_evidence_changed_routes_to_evidence_ledger(monkeypatch):
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    _stub(monkeypatch, ["_plan", "_search_literature_with_langchain_tools",
        "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
        "_classify_papers", "_profile_scientific_data", "_run_arena", "_run_novelty_check",
        "_run_baseline_intake", "_design_experiment", "_run_code_experiment",
        "_evaluate_experiment_result_gate", "_redesign_experiment", "_run_macro_react", "_write_report",
        "_verify_claims", "_revise_report_after_audit", "_translate_report", "_route_intent"])
    async def fake_gate(self, run):
        from app.schemas.feedback_loop import BaselineGateStatus
        run.baseline_gate_status = BaselineGateStatus(research_gate_passed=False)
    monkeypatch.setattr(LangGraphWorkflow, "_evaluate_baseline_gate", fake_gate)
    async def fake_research(self, run):
        run.evidence_changed = True
        run.re_search_round += 1
    monkeypatch.setattr(LangGraphWorkflow, "_re_search_literature", fake_research)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf.run(run)
    names = [s.name for s in run.steps if s.status == "completed"]
    assert "re_search_literature" in names
    # evidence_ledger re-run (appears after re_search in step order)
    # Use last occurrence since evidence_ledger runs initially + after re_search
    last_evidence_idx = max(i for i, n in enumerate(names) if n == "evidence_ledger")
    assert last_evidence_idx > names.index("re_search_literature")


@pytest.mark.asyncio
async def test_completed_negative_routes_to_experiment_redesign_then_report(monkeypatch):
    wf = LangGraphWorkflow(Settings(dashscope_api_key="", max_papers=2, workflow_engine="langgraph"))
    _stub(monkeypatch, ["_plan", "_search_literature_with_langchain_tools",
        "_verify_citations_with_langchain_tools", "_build_evidence", "_mine_literature",
        "_classify_papers", "_profile_scientific_data", "_run_arena", "_run_novelty_check",
        "_run_baseline_intake",
        "_evaluate_baseline_gate", "_design_experiment", "_re_search_literature",
        "_evaluate_experiment_result_gate",
        "_write_report", "_verify_claims", "_revise_report_after_audit", "_translate_report",
        "_route_intent"])
    call_count = {"ce": 0}
    async def fake_ce(self, run):
        call_count["ce"] += 1
        from app.schemas.code_experiment import CodeExperimentResult, ComparisonResult, ExperimentSummary
        if call_count["ce"] == 1:
            run.code_experiment = CodeExperimentResult(trigger="initial",
                comparison=ComparisonResult(outcome="completed_negative", method_beats_baseline=False,
                                            method_metrics={"accuracy":0.7}, baseline_metrics={"accuracy":0.9}),
                summary=ExperimentSummary(outcome="completed_negative", tests_pass=True,
                                          method_beats_baseline=False, best_metric=0.7))
        else:
            run.code_experiment = CodeExperimentResult(trigger="redesign",
                comparison=ComparisonResult(outcome="completed_positive", method_beats_baseline=True,
                                            method_metrics={"accuracy":0.9}, baseline_metrics={"accuracy":0.5}),
                summary=ExperimentSummary(outcome="completed_positive", method_beats_baseline=True, best_metric=0.9))
        run.code_experiment_mode = None
    monkeypatch.setattr(LangGraphWorkflow, "_run_code_experiment", fake_ce)
    async def fake_redesign(self, run):
        run.experiment_redesign_round += 1
        run.code_experiment_mode = "redesign"
    monkeypatch.setattr(LangGraphWorkflow, "_redesign_experiment", fake_redesign)
    run = ResearchRun(domain="seismic_event_classification", question="q",
                      constraints=ResearchConstraints(), mode="discovery")
    await wf.run(run)
    assert call_count["ce"] == 2  # initial + redesign
    assert run.experiment_redesign_round == 1
    names = [s.name for s in run.steps if s.status == "completed"]
    assert "experiment_redesign" in names
    assert names.index("experiment_redesign") > names.index("experiment_result_gate")
