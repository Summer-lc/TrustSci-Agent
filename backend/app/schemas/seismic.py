from pydantic import BaseModel, Field


class SeismicDataProfile(BaseModel):
    dataset_name: str
    num_events: int
    labels: dict[str, int] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=list)
    sampling_rate: int | None = None
    window_seconds: int | None = None
    split_strategy: str = "event_level"
    risks: list[str] = Field(default_factory=list)
    source_path: str | None = None
