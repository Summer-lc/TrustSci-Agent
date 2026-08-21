# backend/app/agents/code_writer_agent.py
"""CodeWriterAgent — LCEL agent that writes/repairs the harness model.py.

Two prompt modes: 'initial' (from Top1 hypothesis + experiment plan + harness
interface spec) and 'repair' (from current source + last traceback). LLM output
is Python source (not JSON), so a custom _CodeExtractor pulls the code block
and falls back to a skeleton SeismicModel on any failure — guaranteeing the
harness can always produce a comparison (even if completed_negative)."""
from __future__ import annotations

import re
from typing import Literal

from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient, LLMResponseFormat
from app.llm.langchain_adapter import LLMClientRunnable, build_agent_prompt
from app.schemas.experiment import ExperimentPlan
from app.schemas.hypothesis import Hypothesis

FALLBACK_MODEL_PY = '''"""Skeleton SeismicModel emitted when the LLM output is unusable.
Not meant to win — meant to keep the harness running so a comparison is produced."""
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
'''

SYSTEM_PROMPT = """You are the Code Writer for TrustSci-Agent v3 seismic Code Experiment Loop.
You write ONLY the file `model.py` — a single Python class `SeismicModel` with:
  def fit(self, X, y) -> self
  def predict(self, X) -> array-like of labels
X is a numpy array of shape (N, 3, 3000): N events, 3 channels (Z/N/E), 3000 samples @ 100Hz.
Labels are one of: earthquake, explosion, noise.
Available libs: numpy, scikit-learn (sklearn). Do NOT import torch/scipy/anything not installed.
Do NOT read files, do NOT use network. fit/predict must be self-contained.
Return ONLY a single ```python code block``` containing model.py — no prose.
The class MUST be named `SeismicModel` and implement both fit() and predict().
"""

INITIAL_TEMPLATE = """Hypothesis (Top1 from Arena):
{hypothesis}

Experiment plan:
{plan}

Write model.py implementing the hypothesis as SeismicModel. Beat the baseline
(per-channel time-domain statistics + LogisticRegression) using the hypothesis's
approach (e.g. spectral / multi-channel features)."""

REPAIR_TEMPLATE = """The previous model.py failed. Current source:
```python
{current_source}
```

Traceback / failure:
```
{traceback}
```

Rewrite model.py (full file, single ```python block```) fixing the failure. Keep
the SeismicModel class with fit()/predict()."""

MACRO_TEMPLATE = """The previous model.py ran but performed poorly. Current source:
```python
{current_source}
```

Last metrics (method): {last_metrics}
Comparison: {last_comparison}
Notes: {notes}

The model is not a crash (tests pass) but the result is bad. Rewrite model.py with a
DIFFERENT architecture/approach to improve the metric (e.g. different feature extractor,
different classifier, multi-channel aggregation). Keep the SeismicModel class with
fit()/predict(). Return a single ```python block```."""


class _CodeExtractor(Runnable):
    def __init__(self, fallback: str) -> None:
        super().__init__()
        self.fallback = fallback

    def parse(self, content: object) -> str:
        if not isinstance(content, str):
            return self.fallback
        m = re.search(r"```(?:python)?\s*(.*?)```", content, re.S)
        text = m.group(1) if m else content
        text = text.strip()
        if "class SeismicModel" not in text:
            return self.fallback
        if "def fit" not in text or "def predict" not in text:
            return self.fallback
        return text

    def invoke(self, input, config=None, **kwargs):
        return self.parse(input)

    async def ainvoke(self, input, config=None, **kwargs):
        return self.parse(input)


class CodeWriterAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm
        self._prompt = build_agent_prompt(SYSTEM_PROMPT)

    async def arun(
        self,
        mode: Literal["initial", "repair", "macro"],
        hypothesis: Hypothesis | None,
        experiment_plan: ExperimentPlan | None,
        *,
        current_source: str | None = None,
        traceback: str | None = None,
        last_metrics: dict | None = None,
        last_comparison: dict | None = None,
        notes: list[str] | None = None,
        run_id: str,
    ) -> str:
        if mode == "repair":
            user_prompt = REPAIR_TEMPLATE.format(
                current_source=current_source or "",
                traceback=traceback or "(no traceback)",
            )
        elif mode == "macro":
            user_prompt = MACRO_TEMPLATE.format(
                current_source=current_source or "",
                last_metrics=last_metrics or {},
                last_comparison=last_comparison or {},
                notes=notes or [],
            )
        else:
            user_prompt = INITIAL_TEMPLATE.format(
                hypothesis=_fmt_hypothesis(hypothesis),
                plan=_fmt_plan(experiment_plan),
            )
        if self.llm is None:
            return FALLBACK_MODEL_PY
        chain = (
            self._prompt
            | LLMClientRunnable(self.llm, response_format=LLMResponseFormat.text).bind(
                fallback=FALLBACK_MODEL_PY, run_id=run_id, agent="code_writer")
            | _CodeExtractor(FALLBACK_MODEL_PY)
        )
        return await chain.ainvoke({"user_prompt": user_prompt})


def _fmt_hypothesis(h: Hypothesis | None) -> str:
    if h is None:
        return "(none)"
    return f"statement: {h.statement}\nrationale: {h.rationale}\nverification_path: {h.verification_path}"


def _fmt_plan(p: ExperimentPlan | None) -> str:
    if p is None:
        return "(none)"
    return (f"datasets: {p.datasets}\nbaselines: {p.baselines}\n"
            f"metrics: {p.metrics}\nsteps: {p.experiment_steps}\n"
            f"expected: {p.expected_results}")
