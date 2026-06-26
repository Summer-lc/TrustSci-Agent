from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(str, Enum):
    created = "created"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class AgentStep(BaseModel):
    name: str
    status: str = "pending"
    summary: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
