from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class MetricObservation(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    value: float
    unit: str | None = None
    split: str | None = None
    notes: str | None = None

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric value must be finite")
        return value


class AblationObservation(BaseModel):
    component: str = Field(min_length=1, max_length=200)
    metrics: list[MetricObservation] = Field(default_factory=list)
    notes: str | None = None


class ExperimentAssistanceInput(BaseModel):
    objective: str = Field(min_length=3, max_length=2000)
    method_summary: str = Field(min_length=3, max_length=4000)
    source_code: str | None = Field(default=None, max_length=200_000)
    dataset_description: str = ""
    baseline_name: str = ""
    baseline_metrics: list[MetricObservation] = Field(default_factory=list)
    method_metrics: list[MetricObservation] = Field(default_factory=list)
    ablations: list[AblationObservation] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    author_notes: str = ""

    @model_validator(mode="after")
    def require_observation(self):
        if not self.method_metrics and not any(item.strip() for item in self.logs):
            raise ValueError("at least one method metric or experiment log is required")
        return self


class MetricDelta(BaseModel):
    name: str
    baseline: float | None = None
    method: float | None = None
    delta: float | None = None


class ResultEvaluation(BaseModel):
    verdict: Literal["pass", "partial", "fail"] = "partial"
    metric_deltas: list[MetricDelta] = Field(default_factory=list)
    supported_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    data_quality_warnings: list[str] = Field(default_factory=list)
    reasoning: str = ""


class AblationFinding(BaseModel):
    component: str
    effect: str
    metric_deltas: list[MetricDelta] = Field(default_factory=list)


class AblationAnalysis(BaseModel):
    coverage: Literal["complete", "partial", "missing"] = "missing"
    findings: list[AblationFinding] = Field(default_factory=list)
    missing_comparisons: list[str] = Field(default_factory=list)
    summary: str = ""


class ResultInterpretation(BaseModel):
    conclusions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    failure_explanation: str | None = None
    next_experiments: list[str] = Field(default_factory=list)
    evidence_boundary: str = ""
