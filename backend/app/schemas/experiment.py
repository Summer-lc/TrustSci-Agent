from pydantic import BaseModel, Field


class ExperimentPlan(BaseModel):
    datasets: list[str]
    source: str
    target: str
    baselines: list[str]
    metrics: list[str]
    experiment_steps: list[str]
    expected_results: str
    failure_modes: list[str] = Field(default_factory=list)

