from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import utc_now


class LLMCallLog(BaseModel):
    call_id: str
    run_id: str | None = None
    agent: str
    model: str
    provider: str = "bailian-qwen"
    llm_enabled: bool
    status: str
    fallback_used: bool
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    duration_ms: int | None = None
    system_prompt: str
    user_prompt: str
    response: Any
    token_usage: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    log_path: str | None = None

