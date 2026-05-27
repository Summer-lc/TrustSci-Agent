from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import utc_now


class DatasetProfile(BaseModel):
    name: str
    source: str
    source_url: str | None = None
    rows: int | None = None
    fields: list[str] = Field(default_factory=list)
    target: str | None = None
    task_type: str
    availability: str = "available"
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaselineResultCard(BaseModel):
    name: str
    dataset: str
    target: str
    model: str
    train_rows: int
    test_rows: int
    metrics: dict[str, float]
    result_summary: str
    artifact_path: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

