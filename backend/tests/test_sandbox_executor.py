# backend/tests/test_sandbox_executor.py
import time

from app.tools.sandbox_executor import SandboxExecutor, SandboxRunResult


def test_prepare_copies_harness_and_writes_model(tmp_path):
    sb = tmp_path / "sb"
    ex = SandboxExecutor(harness_dir="experiments/seismic_event_classification", timeout=10)
    ex.prepare(sb, "class SeismicModel:\n    pass\n")
    for fn in ("data.py", "baseline.py", "train.py", "tests.py", "harness_manifest.json", "model.py"):
        assert (sb / fn).exists(), fn
    assert (sb / "model.py").read_text().startswith("class SeismicModel")


def test_prepare_clears_stale_artifacts(tmp_path):
    sb = tmp_path / "sb"
    sb.mkdir()
    for name in ("metrics.json", "comparison.json", "tests_failed.flag"):
        (sb / name).write_text("stale", encoding="utf-8")
    cache = sb / "__pycache__"
    cache.mkdir()
    (cache / "model.pyc").write_text("stale", encoding="utf-8")
    ex = SandboxExecutor(harness_dir="experiments/seismic_event_classification", timeout=10)
    ex.prepare(sb, "class SeismicModel:\n    pass\n")
    for name in ("metrics.json", "comparison.json", "tests_failed.flag", "__pycache__"):
        assert not (sb / name).exists(), name


def test_run_rejects_non_whitelisted_script(tmp_path):
    ex = SandboxExecutor(harness_dir="experiments/seismic_event_classification", timeout=5)
    ex.prepare(tmp_path / "sb", "class SeismicModel:\n    pass\n")
    try:
        ex.run(tmp_path / "sb", "evil.py")
        assert False, "should have raised"
    except ValueError:
        pass


def test_run_captures_exit_code_and_stdout(tmp_path):
    # Use a tmp harness dir whose tests.py just prints + exits 0
    import shutil, pathlib
    hd = tmp_path / "harness"; hd.mkdir()
    (hd / "data.py").write_text("LABELS=()\ndef load_split(s):\n    import numpy as np; return np.zeros((1,3,10)), np.array([])\n")
    (hd / "baseline.py").write_text("class BaselineModel:\n    pass\n")
    (hd / "train.py").write_text("print('hello from train')\n")
    (hd / "tests.py").write_text("print('hi from tests')\n")
    (hd / "harness_manifest.json").write_text("{}\n")
    ex = SandboxExecutor(harness_dir=hd, timeout=10)
    sb = tmp_path / "sb"
    ex.prepare(sb, "class SeismicModel:\n    pass\n")
    r = ex.run(sb, "tests.py")
    assert isinstance(r, SandboxRunResult)
    assert r.exit_code == 0
    assert "hi from tests" in r.stdout
    assert not r.timed_out
    r2 = ex.run(sb, "train.py")
    assert "hello from train" in r2.stdout


def test_run_reports_timeout(tmp_path):
    import pathlib
    hd = tmp_path / "harness"; hd.mkdir()
    (hd / "data.py").write_text("LABELS=()\n")
    (hd / "baseline.py").write_text("class BaselineModel: pass\n")
    (hd / "train.py").write_text("import time; time.sleep(5)\n")
    (hd / "tests.py").write_text("import time; time.sleep(5)\n")
    (hd / "harness_manifest.json").write_text("{}\n")
    ex = SandboxExecutor(harness_dir=hd, timeout=1)
    sb = tmp_path / "sb"
    ex.prepare(sb, "class SeismicModel:\n    pass\n")
    r = ex.run(sb, "tests.py")
    assert r.timed_out is True
    assert r.exit_code == -1
