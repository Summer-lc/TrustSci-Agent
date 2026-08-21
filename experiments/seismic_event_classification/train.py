"""Fixed harness: train baseline + method on train split, eval on test split,
write metrics.json + comparison.json (fixed schema)."""
import json
import pathlib

import numpy as np

from baseline import BaselineModel
from data import load_split
from model import SeismicModel

METRICS_PATH = pathlib.Path("metrics.json")
COMPARISON_PATH = pathlib.Path("comparison.json")


def _metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    acc = float((y_pred == y_true).mean())
    f1s = {}
    for label in sorted(set(y_true) | set(y_pred)):
        tp = int(((y_pred == label) & (y_true == label)).sum())
        fp = int(((y_pred == label) & (y_true != label)).sum())
        fn = int(((y_pred != label) & (y_true == label)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s[label] = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    macro_f1 = float(np.mean(list(f1s.values()))) if f1s else 0.0
    return {"accuracy": acc, "macro_f1": macro_f1, "per_class_f1": f1s}


def main() -> int:
    Xtr, ytr = load_split("train")
    Xte, yte = load_split("test")
    baseline = BaselineModel().fit(Xtr, ytr)
    method = SeismicModel().fit(Xtr, ytr)
    b = _metrics(yte, baseline.predict(Xte))
    m = _metrics(yte, method.predict(Xte))
    METRICS_PATH.write_text(json.dumps({"baseline": b, "method": m}, indent=2), encoding="utf-8")
    beats = m["accuracy"] > b["accuracy"]
    outcome = "completed_positive" if beats else "completed_negative"
    COMPARISON_PATH.write_text(json.dumps({
        "baseline_source": "harness_trivial",
        "baseline_metrics": b,
        "method_metrics": m,
        "method_beats_baseline": bool(beats),
        "outcome": outcome,
        "notes": [],
    }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
