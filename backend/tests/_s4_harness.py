import importlib.util
from pathlib import Path


def harness_dir() -> Path:
    p = Path(__file__).resolve()
    for parent in (p.parent, *p.parents):
        cand = parent / "experiments" / "seismic_event_classification"
        if cand.is_dir():
            return cand
    raise RuntimeError("experiments/seismic_event_classification not found (mount ./experiments?)")


def load_harness_module(filename: str, modname: str):
    path = harness_dir() / filename
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
