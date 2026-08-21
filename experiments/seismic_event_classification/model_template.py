"""Reference skeleton SeismicModel. The CodeWriterAgent fallback emits a model
like this. LLM-written model.py replaces it at runtime in the sandbox."""
import numpy as np
from sklearn.linear_model import LogisticRegression


class SeismicModel:
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
