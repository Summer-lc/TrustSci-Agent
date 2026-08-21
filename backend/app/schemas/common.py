from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.run_control import StepEvent


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(str, Enum):
    created = "created"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    abandoned = "abandoned"


class AgentStep(BaseModel):
    name: str
    status: str = "pending"
    summary: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
    attempts: int = 0
    error_code: str | None = None
    error_summary: str | None = None
    retryable: bool = False
    skippable: bool = False
    events: list[StepEvent] = Field(default_factory=list)
