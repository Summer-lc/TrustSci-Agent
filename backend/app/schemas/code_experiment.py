from typing import Literal

from pydantic import BaseModel, Field


class AcceptanceGate(BaseModel):
    tests_pass: bool = False
    metrics_generated: bool = False
    baseline_comparison_written: bool = False

    @property
    def all_passed(self) -> bool:
        return self.tests_pass and self.metrics_generated and self.baseline_comparison_written


class ComparisonResult(BaseModel):
    baseline_source: str = "harness_trivial"
    baseline_metrics: dict = Field(default_factory=dict)
    method_metrics: dict = Field(default_factory=dict)
    method_beats_baseline: bool = False
    outcome: Literal["completed_positive", "completed_negative", "failed"] = "failed"
    notes: list[str] = Field(default_factory=list)


class FairComparisonPlan(BaseModel):
    method_name: str = "SeismicModel"
    baseline_source: str = "harness_trivial"
    split_strategy: str = "event_level"
    metrics: list[str] = Field(default_factory=lambda: ["accuracy", "macro_f1"])
    preprocessing: str = "raw waveform, event-level split, no leakage"


class IterEntry(BaseModel):
    round: int
    phase: Literal["initial", "repair"] = "initial"
    model_py_hash: str = ""
    tests_passed: bool = False
    traceback_summary: str | None = None


class DebugEntry(BaseModel):
    round: int
    traceback_full: str | None = None
    patch_diff: str | None = None


class ExperimentSummary(BaseModel):
    outcome: Literal["completed_positive", "completed_negative", "failed"] = "failed"
    tests_pass: bool = False
    method_beats_baseline: bool = False
    baseline_source: str = "harness_trivial"
    best_metric: float | None = None
    failure_reason: str | None = None


class CodeExperimentResult(BaseModel):
    harness_version: str = "seismic_sklearn_v1"
    model_family: str = "sklearn"
    baseline_source: str = "harness_trivial"
    model_py_source: str = ""
    fair_comparison_plan: FairComparisonPlan = Field(default_factory=FairComparisonPlan)
    acceptance_gate: AcceptanceGate = Field(default_factory=AcceptanceGate)
    comparison: ComparisonResult = Field(default_factory=ComparisonResult)
    iteration_log: list[IterEntry] = Field(default_factory=list)
    debug_log: list[DebugEntry] = Field(default_factory=list)
    summary: ExperimentSummary = Field(default_factory=ExperimentSummary)
    trigger: Literal["initial", "macro", "switchback", "redesign"] = "initial"
