"""Acceptance-gate pre-check (runs BEFORE train.py). Verifies the LLM-written
model.py is importable, has the fit/predict interface, and produces predictions
with correct length, valid labels, and no NaN/inf. metrics.json/comparison.json
existence is checked by the workflow AFTER train (not here)."""
import math
import pathlib
import sys
import traceback

import numpy as np

from data import LABELS, load_split


def _has_nan_or_inf(arr) -> bool:
    """Dtype-agnostic NaN/inf check: predictions may be string labels (object
    dtype) with a stray float NaN, which np.isfinite would refuse on object
    arrays. Walk values explicitly."""
    for v in np.asarray(arr).ravel():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return True
    return False


def _run():
    errors = []
    try:
        from model import SeismicModel
        m = SeismicModel()
        if not (hasattr(m, "fit") and hasattr(m, "predict")):
            errors.append("SeismicModel missing fit/predict")
            return errors
    except Exception as e:  # noqa: BLE001
        errors.append(f"model import/interface failed: {e!r}")
        return errors
    try:
        Xtr, ytr = load_split("train")
        Xte, yte = load_split("test")
        m.fit(Xtr, ytr)
        pred = np.asarray(m.predict(Xte))
        if len(pred) != len(yte):
            errors.append(f"len(pred)={len(pred)} != len(y_test)={len(yte)}")
        if not set(np.unique(pred)).issubset(set(LABELS)):
            errors.append(f"pred labels {set(np.unique(pred))} not subset of {set(LABELS)}")
        if _has_nan_or_inf(pred):
            errors.append("predictions contain NaN/inf")
    except Exception:  # noqa: BLE001
        errors.append("fit/predict raised:\n" + traceback.format_exc())
    return errors


def main() -> int:
    errors = _run()
    if errors:
        print("TESTS FAILED:")
        for e in errors:
            print(e)
        pathlib.Path("tests_failed.flag").write_text("failed", encoding="utf-8")
        return 1
    print("TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
