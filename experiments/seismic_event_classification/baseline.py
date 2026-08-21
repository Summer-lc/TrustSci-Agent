"""Fixed weak baseline: per-channel time-domain stats + LogisticRegression.
LLM never edits this. It is the fair-comparison anchor (baseline_source=harness_trivial)."""
import numpy as np
from sklearn.linear_model import LogisticRegression


class BaselineModel:
    def __init__(self):
        self.clf = LogisticRegression(max_iter=2000, class_weight="balanced")

    def _features(self, X):
        return np.concatenate(
            [X.mean(2), X.std(2), np.abs(X).max(2), (X ** 2).mean(2)], axis=1)

    def fit(self, X, y):
        self.clf.fit(self._features(X), y)
        return self

    def predict(self, X):
        return self.clf.predict(self._features(X))
