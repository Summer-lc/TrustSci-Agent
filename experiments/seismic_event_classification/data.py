# experiments/seismic_event_classification/data.py
"""Deterministic synthetic seismic waveforms for the S4 Code Experiment Loop.

120 events x 3 channels (Z/N/E) x 30s @ 100Hz = 3000 samples. Three classes
designed so time-domain statistics (mean/std/peak/energy) are UNINFORMATIVE
but spectral content separates them: earthquake = low-freq sine (1-3 Hz),
explosion = high-freq sine (10-20 Hz), noise = broadband white — each
normalized to unit RMS so std/energy match across classes (sines share the
same peak too; only noise has a higher Gaussian peak). A frequency-feature
model therefore genuinely beats a time-domain-statistics baseline; a dumb
model that only uses time stats ties the baseline (completed_negative).
Per-channel rotation/attenuation makes multi-channel features useful.

Pure numpy (no scipy). Seed fixed -> reproducible. Real STEAD subset lands in S7.
"""
import pathlib

import numpy as np

LABELS = ("earthquake", "explosion", "noise")
COUNTS = {"earthquake": 60, "explosion": 35, "noise": 25}
SAMPLING_RATE = 100
WINDOW_SECONDS = 30
CHANNELS = ("Z", "N", "E")
SEED = 20260629
_N = WINDOW_SECONDS * SAMPLING_RATE  # 3000


def _unit_rms(sig: np.ndarray) -> np.ndarray:
    return sig / (np.sqrt(np.mean(sig ** 2)) + 1e-8)


def _gen_event(label: str, n: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SAMPLING_RATE
    if label == "earthquake":
        f = rng.uniform(1.0, 3.0)
        sig = np.sin(2 * np.pi * f * t)
    elif label == "explosion":
        f = rng.uniform(10.0, 20.0)
        sig = np.sin(2 * np.pi * f * t)
    else:  # noise
        sig = rng.standard_normal(n)
    # Unit RMS so mean/std/energy are class-invariant and sines share the same
    # peak — only spectral content (and noise's higher Gaussian peak) separates
    # classes. This is what makes a frequency-feature model beat a time-stats
    # baseline without rigging the data.
    return _unit_rms(sig)


def generate_waveforms():
    """Return (X(120,3,3000), y(120,), splits(120,)) deterministically."""
    rng = np.random.default_rng(SEED)
    nchan = len(CHANNELS)
    X, y, splits = [], [], []
    eid = 0
    for label, count in COUNTS.items():
        for _ in range(count):
            eid += 1
            base = _gen_event(label, _N, rng)
            wave = np.zeros((nchan, _N))
            for c in range(nchan):
                amp = 1.0 - 0.05 * c
                # Scalar per-channel attenuation only — NO time-shift rotation,
                # because np.roll(base, 1) is a frequency-dependent phase shift
                # (high-freq sines degrade faster across channels) that leaks
                # spectral info into per-channel std and lets a time-stats
                # baseline separate eq from explosion. Scalar amp keeps std
                # class-invariant; only peak (noise's higher Gaussian max vs
                # sines' sqrt(2)) leaks, capping the baseline well below the
                # freq-feature model.
                wave[c] = amp * base + 0.05 * rng.standard_normal(_N)
            X.append(wave)
            y.append(label)
            # 60% train / 20% val / 20% test, deterministic per event id.
            splits.append(["train", "train", "train", "val", "test"][eid % 5])
    return np.stack(X), np.array(y), np.array(splits)


def load_split(split: str):
    X, y, splits = generate_waveforms()
    mask = splits == split
    return X[mask], y[mask]


def save_npz(path) -> None:
    X, y, splits = generate_waveforms()
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez(p, X=X, y=y, splits=splits, channels=np.array(CHANNELS))


if __name__ == "__main__":
    save_npz(pathlib.Path("data/seismic_demo/waveforms.npz"))
    print("wrote data/seismic_demo/waveforms.npz")
