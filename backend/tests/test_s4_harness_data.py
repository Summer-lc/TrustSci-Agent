import numpy as np

from _s4_harness import load_harness_module


def test_waveforms_deterministic_and_shaped() -> None:
    data = load_harness_module("data.py", "s4_data")
    X1, y1, s1 = data.generate_waveforms()
    X2, y2, s2 = data.generate_waveforms()
    assert X1.shape == (120, 3, 3000)
    assert len(y1) == 120 and len(s1) == 120
    np.testing.assert_array_equal(X1, X2)
    assert set(np.unique(y1)) == set(data.LABELS)
    assert set(np.unique(s1)) == {"train", "val", "test"}


def test_load_split_consistency() -> None:
    data = load_harness_module("data.py", "s4_data")
    Xtr, ytr = data.load_split("train")
    Xte, yte = data.load_split("test")
    assert Xtr.shape[1:] == (3, 3000)
    assert len(Xtr) + len(data.load_split("val")[0]) + len(Xte) == 120
    assert set(ytr).issubset(set(data.LABELS))


def test_waveforms_separable_by_frequency_not_time_stats() -> None:
    """Sanity: a frequency-feature classifier beats a time-domain-stats baseline.
    Proves the synthetic data carries real separable signal (not rigged, but learnable)."""
    from sklearn.linear_model import LogisticRegression

    data = load_harness_module("data.py", "s4_data")
    X, y, splits = data.generate_waveforms()
    Xtr, ytr = X[splits == "train"], y[splits == "train"]
    Xte, yte = X[splits == "test"], y[splits == "test"]

    def time_feats(X):
        return np.concatenate(
            [X.mean(2), X.std(2), np.abs(X).max(2), (X ** 2).mean(2)], axis=1)

    def freq_feats(X):
        n = X.shape[2]
        spec = np.abs(np.fft.rfft(X, axis=2))
        freqs = np.fft.rfftfreq(n, d=1.0 / data.SAMPLING_RATE)
        peak = freqs[spec.argmax(2)]  # (N, C)
        bands = [(0, 3), (3, 10), (10, 30)]
        band_e = [spec[:, :, (freqs >= lo) & (freqs < hi)].sum(2) for lo, hi in bands]
        return np.concatenate([peak] + band_e, axis=1)

    baseline = LogisticRegression(max_iter=2000, class_weight="balanced").fit(time_feats(Xtr), ytr)
    method = LogisticRegression(max_iter=2000, class_weight="balanced").fit(freq_feats(Xtr), ytr)
    b_acc = (baseline.predict(time_feats(Xte)) == yte).mean()
    m_acc = (method.predict(freq_feats(Xte)) == yte).mean()
    assert m_acc > b_acc, f"freq feats must beat time stats: {m_acc} vs {b_acc}"
    assert m_acc > 0.8, f"data must be learnable: {m_acc}"
