from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


BaselineStrategy = Literal["manual_upload", "ai_generated", "none"]


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


class ManualBaselineInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    code_text: str | None = Field(default=None, max_length=200_000)
    repository_url: str | None = Field(default=None, max_length=2000)
    run_command: str | None = Field(default=None, max_length=1000)
    dataset_description: str = ""
    metrics: list[MetricObservation] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def require_useful_content(self):
        has_text = any(
            bool((value or "").strip())
            for value in (self.description, self.code_text, self.repository_url, self.run_command, self.notes)
        )
        if not self.metrics and not has_text:
            raise ValueError("manual baseline requires metrics, code, repository, command, description, or notes")
        return self


class BaselineIntakeRequest(BaseModel):
    strategy: BaselineStrategy
    manual: ManualBaselineInput | None = None

    @model_validator(mode="after")
    def validate_strategy_payload(self):
        if self.strategy == "manual_upload" and self.manual is None:
            raise ValueError("manual baseline payload is required for manual_upload strategy")
        if self.strategy != "manual_upload" and self.manual is not None:
            raise ValueError("manual baseline payload is only allowed for manual_upload strategy")
        return self


class BaselineIntake(BaseModel):
    strategy: BaselineStrategy
    source_type: Literal["manual_upload", "ai_generated", "unavailable"]
    trust_level: Literal["user_provided", "runnable_demo", "insufficient"]
    name: str = ""
    description: str = ""
    metrics: list[MetricObservation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance_notes: list[str] = Field(default_factory=list)
