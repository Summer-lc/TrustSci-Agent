# backend/tests/test_s4_harness.py
import json
import subprocess
import textwrap
from pathlib import Path

from _s4_harness import harness_dir, load_harness_module


def _write_model(sandbox: Path, source: str) -> None:
    (sandbox / "model.py").write_text(source, encoding="utf-8")


def _copy_harness(sandbox: Path) -> None:
    import shutil
    for fn in ("data.py", "baseline.py", "train.py", "tests.py", "harness_manifest.json"):
        shutil.copy(harness_dir() / fn, sandbox / fn)


def _run(script: str, sandbox: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["python", script], cwd=sandbox, capture_output=True, text=True, timeout=120)


GOOD_MODEL = textwrap.dedent('''
    import numpy as np
    from sklearn.linear_model import LogisticRegression

    class SeismicModel:
        def __init__(self):
            self.clf = LogisticRegression(max_iter=2000, class_weight="balanced")
        def _f(self, X):
            return np.concatenate([X.mean(2), X.std(2), np.abs(X).max(2), (X**2).mean(2)], axis=1)
        def fit(self, X, y):
            self.clf.fit(self._f(X), y); return self
        def predict(self, X):
            return self.clf.predict(self._f(X))
''')

BAD_SHAPE_MODEL = textwrap.dedent('''
    import numpy as np
    class SeismicModel:
        def fit(self, X, y): return self
        def predict(self, X):
            # wrong length on purpose
            return np.array(["earthquake"] * (len(X) - 1))
''')

NAN_MODEL = textwrap.dedent('''
    import numpy as np
    class SeismicModel:
        def fit(self, X, y): return self
        def predict(self, X):
            out = np.array(["earthquake"] * len(X), dtype=object)
            out[0] = np.nan
            return out
''')

BAD_LABEL_MODEL = textwrap.dedent('''
    import numpy as np
    class SeismicModel:
        def fit(self, X, y): return self
        def predict(self, X):
            return np.array(["covid"] * len(X))
''')


def test_tests_py_passes_good_model(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, GOOD_MODEL)
    r = _run("tests.py", sb)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "TESTS PASSED" in r.stdout


def test_tests_py_catches_shape_mismatch(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, BAD_SHAPE_MODEL)
    r = _run("tests.py", sb)
    assert r.returncode == 1
    assert (sb / "tests_failed.flag").exists()


def test_tests_py_catches_nan_predictions(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, NAN_MODEL)
    r = _run("tests.py", sb)
    assert r.returncode == 1


def test_tests_py_catches_invalid_labels(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, BAD_LABEL_MODEL)
    r = _run("tests.py", sb)
    assert r.returncode == 1


def test_train_py_writes_artifacts_and_comparison_schema(tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    _copy_harness(sb); _write_model(sb, GOOD_MODEL)
    r = _run("train.py", sb)
    assert r.returncode == 0, r.stdout + r.stderr
    comp = json.loads((sb / "comparison.json").read_text())
    assert set(comp) == {"baseline_source", "baseline_metrics", "method_metrics",
                         "method_beats_baseline", "outcome", "notes"}
    assert comp["baseline_source"] == "harness_trivial"
    assert comp["outcome"] in {"completed_positive", "completed_negative"}
    assert "accuracy" in comp["method_metrics"]
    metrics = json.loads((sb / "metrics.json").read_text())
    assert "baseline" in metrics and "method" in metrics


def test_manifest_shape():
    m = json.loads((harness_dir() / "harness_manifest.json").read_text())
    assert m["model_family"] == "sklearn"
    assert m["harness_version"] == "seismic_sklearn_v1"
    assert m["max_repair_rounds"] == 3
    assert m["baseline_source"] == "harness_trivial"
