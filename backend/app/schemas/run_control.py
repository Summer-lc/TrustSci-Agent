from datetime import datetime
from typing import Literal

from pydantic import BaseModel


StepStatus = Literal[
    "pending",
    "running",
    "retrying",
    "completed",
    "waiting_action",
    "skipped",
    "failed",
    "paused",
]


class StepEvent(BaseModel):
    event: Literal[
        "started",
        "retrying",
        "completed",
        "failed",
        "retried",
        "skipped",
        "recovered",
    ]
    at: datetime
    detail: str = ""


class RunActionRequest(BaseModel):
    action: Literal["retry", "skip"]


class PaperPreviewRequest(BaseModel):
    paper_id: str
    source_url: str


class PaperPreviewResult(BaseModel):
    paper_id: str
    source_url: str
    kind: Literal["web_snapshot", "metadata_only"]
    title: str = ""
    screenshot_url: str | None = None
    original_url: str
    cached: bool = False
    error_summary: str | None = None
