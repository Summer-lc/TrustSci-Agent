# backend/tests/test_code_experiment_loop.py
import json

import pytest

from app.agents.code_writer_agent import FALLBACK_MODEL_PY
from app.config import Settings
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis
from app.schemas.run import ResearchConstraints, ResearchRun
from app.workflows.scientist_workflow import ScientistWorkflow


GOOD_SRC = "class SeismicModel:\n    def fit(self,X,y): return self\n    def predict(self,X): return ['earthquake']*len(X)\n"


class FakeCodeWriter:
    def __init__(self, sources):
        self.sources = list(sources)
        self.calls = []
    async def arun(self, mode, hypothesis, plan, *, current_source=None, traceback=None, run_id):
        self.calls.append((mode, traceback))
        return self.sources.pop(0) if self.sources else GOOD_SRC


class _R:
    def __init__(self, exit_code, stderr=""):
        self.exit_code = exit_code
        self.stdout = ""
        self.stderr = stderr
        self.timed_out = False


class FakeSandbox:
    """Parametrizable fake: tests_results is a list of (exit_code, stderr)
    consumed one per tests.py call. train.py writes metrics+comparison from
    method_acc/baseline_acc unless train_crash=True."""
    def __init__(self, *, tests_results, method_acc=0.9, baseline_acc=0.5,
                 train_crash=False, write_artifacts=True):
        self.tests_results = list(tests_results)
        self.method_acc = method_acc
        self.baseline_acc = baseline_acc
        self.train_crash = train_crash
        self.write_artifacts = write_artifacts
        self.scripts_run: list[str] = []
    def prepare(self, sandbox_dir, model_py_source):
        import pathlib
        pathlib.Path(sandbox_dir).mkdir(parents=True, exist_ok=True)
    def clear_artifacts(self, sandbox_dir):
        import pathlib
        for name in ("metrics.json", "comparison.json", "tests_failed.flag"):
            path = pathlib.Path(sandbox_dir, name)
            if path.exists():
                path.unlink()
    def run(self, sandbox_dir, script):
        import json, pathlib
        self.scripts_run.append(script)
        if script == "tests.py":
            ec, stderr = self.tests_results.pop(0)
            return _R(ec, stderr)
        if script == "train.py":
            if self.train_crash:
                return _R(1, "train boom")
            if self.write_artifacts:
                pathlib.Path(sandbox_dir, "metrics.json").write_text(json.dumps(
                    {"baseline": {"accuracy": self.baseline_acc},
                     "method": {"accuracy": self.method_acc}}))
                beats = self.method_acc > self.baseline_acc
                pathlib.Path(sandbox_dir, "comparison.json").write_text(json.dumps({
                    "baseline_source": "harness_trivial",
                    "baseline_metrics": {"accuracy": self.baseline_acc},
                    "method_metrics": {"accuracy": self.method_acc},
                    "method_beats_baseline": bool(beats),
                    "outcome": "completed_positive" if beats else "completed_negative",
                    "notes": []}))
            return _R(0)
        raise ValueError(f"unexpected script {script}")


def _wf_with(code_writer, sandbox):
    wf = ScientistWorkflow(Settings(dashscope_api_key="", max_papers=2))
    wf.code_writer = code_writer
    wf.sandbox_executor = sandbox
    return wf


def _run():
    r = ResearchRun(domain="seismic_event_classification", question="q",
                    constraints=ResearchConstraints(), mode="discovery")
    r.hypotheses = [Hypothesis(hypothesis_id="H1", statement="s", rationale="r",
                               novelty_claim="n", verification_path="v", selected=True)]
    r.experiment_plan = ExperimentPlan(datasets=["d"], source="s", target="t",
                                       baselines=["b"], metrics=["accuracy"],
                                       experiment_steps=["x"], expected_results="e")
    return r


@pytest.mark.asyncio
async def test_scenario_tests_pass_completed_positive(tmp_path, monkeypatch):
    wf = _wf_with(FakeCodeWriter([GOOD_SRC]),
                  FakeSandbox(tests_results=[(0, "")], method_acc=0.9, baseline_acc=0.5))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce is not None
    assert ce.acceptance_gate.tests_pass is True
    assert ce.acceptance_gate.metrics_generated is True
    assert ce.acceptance_gate.baseline_comparison_written is True
    assert ce.comparison.outcome == "completed_positive"
    assert ce.summary.outcome == "completed_positive"
    assert ce.summary.method_beats_baseline is True
    assert ce.summary.best_metric == 0.9
    assert len(ce.iteration_log) == 1
    assert ce.iteration_log[0].phase == "initial"


@pytest.mark.asyncio
async def test_scenario_tests_fail_three_rounds_then_failed_skip_train(tmp_path, monkeypatch):
    wf = _wf_with(FakeCodeWriter([GOOD_SRC, GOOD_SRC, GOOD_SRC]),
                  FakeSandbox(tests_results=[(1, "err1"), (1, "err2"), (1, "err3")]))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce.acceptance_gate.tests_pass is False
    assert ce.acceptance_gate.metrics_generated is False
    assert ce.acceptance_gate.baseline_comparison_written is False
    assert ce.comparison.outcome == "failed"
    assert ce.summary.outcome == "failed"
    assert ce.summary.failure_reason
    assert len(ce.iteration_log) == 3
    # train.py must NEVER have been called (tests never passed)
    assert "train.py" not in wf.sandbox_executor.scripts_run
    # repair was attempted between rounds (2 repair calls for 3 rounds)
    assert [c[0] for c in wf.code_writer.calls] == ["initial", "repair", "repair"]


@pytest.mark.asyncio
async def test_scenario_fallback_skeleton_then_completed_negative(tmp_path, monkeypatch):
    # CodeWriter returns the (interface-valid) fallback skeleton; tests pass;
    # train produces a comparison where method does NOT beat baseline.
    wf = _wf_with(FakeCodeWriter([FALLBACK_MODEL_PY]),
                  FakeSandbox(tests_results=[(0, "")], method_acc=0.4, baseline_acc=0.8))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce.acceptance_gate.tests_pass is True
    assert ce.comparison.outcome == "completed_negative"
    assert ce.summary.outcome == "completed_negative"
    assert ce.summary.method_beats_baseline is False
    assert ce.summary.best_metric == 0.4


@pytest.mark.asyncio
async def test_scenario_train_crash_then_failed(tmp_path, monkeypatch):
    # tests pass round 1, but train.py crashes (no artifacts) -> failed
    wf = _wf_with(FakeCodeWriter([GOOD_SRC]),
                  FakeSandbox(tests_results=[(0, "")], train_crash=True, write_artifacts=False))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce.acceptance_gate.tests_pass is True
    assert ce.acceptance_gate.metrics_generated is False
    assert ce.acceptance_gate.baseline_comparison_written is False
    assert ce.comparison.outcome == "failed"
    assert ce.summary.outcome == "failed"
    assert ce.summary.failure_reason
    assert ce.summary.best_metric is None


@pytest.mark.asyncio
async def test_train_failure_ignores_stale_artifacts(tmp_path, monkeypatch):
    wf = _wf_with(FakeCodeWriter([GOOD_SRC]),
                  FakeSandbox(tests_results=[(0, "")], train_crash=True, write_artifacts=False))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    r = _run()
    sandbox_dir = tmp_path / "outputs" / r.run_id / "sandbox"
    sandbox_dir.mkdir(parents=True)
    (sandbox_dir / "metrics.json").write_text(json.dumps(
        {"baseline": {"accuracy": 0.1}, "method": {"accuracy": 1.0}}), encoding="utf-8")
    (sandbox_dir / "comparison.json").write_text(json.dumps({
        "baseline_source": "harness_trivial",
        "baseline_metrics": {"accuracy": 0.1},
        "method_metrics": {"accuracy": 1.0},
        "method_beats_baseline": True,
        "outcome": "completed_positive",
        "notes": []
    }), encoding="utf-8")
    await wf._run_code_experiment(r)
    ce = r.code_experiment
    assert ce.acceptance_gate.tests_pass is True
    assert ce.acceptance_gate.metrics_generated is False
    assert ce.acceptance_gate.baseline_comparison_written is False
    assert ce.comparison.outcome == "failed"
    assert ce.summary.outcome == "failed"
    assert "train.py failed" in (ce.summary.failure_reason or "")


@pytest.mark.asyncio
async def test_non_seismic_skips_code_experiment():
    wf = _wf_with(FakeCodeWriter([]), FakeSandbox(tests_results=[]))
    r = ResearchRun(domain="energy_materials", question="q", constraints=ResearchConstraints())
    await wf._run_code_experiment(r)
    assert r.code_experiment is None  # non-seismic: no-op, no result attached


@pytest.mark.asyncio
async def test_loop_crash_attaches_failed_result_and_does_not_raise(tmp_path, monkeypatch):
    # An unexpected exception inside the loop (e.g. sandbox.run raises non-Timeout) must
    # be caught: run.code_experiment is attached with outcome=failed, no exception escapes.
    wf = _wf_with(FakeCodeWriter([GOOD_SRC]), FakeSandbox(tests_results=[(0, "")]))
    monkeypatch.setattr(wf.settings, "data_dir", tmp_path)
    def boom(sandbox_dir, script):
        raise OSError("disk on fire")
    wf.sandbox_executor.run = boom  # type: ignore[assignment]
    r = _run()
    await wf._run_code_experiment(r)  # must NOT raise
    assert r.code_experiment is not None
    assert r.code_experiment.summary.outcome == "failed"
    assert r.code_experiment.summary.failure_reason is not None
    assert "disk on fire" in r.code_experiment.summary.failure_reason
