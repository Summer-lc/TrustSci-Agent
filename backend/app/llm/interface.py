from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class LLMResponseFormat(str, Enum):
    json = "json"
    text = "text"


class LLMRequest(BaseModel):
    system: str
    user: str
    fallback: Any
    response_format: LLMResponseFormat = LLMResponseFormat.json
    run_id: str | None = None
    agent: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    content: Any
    provider: str
    model: str
    fallback_used: bool = False


class LLMClient(Protocol):
    provider: str

    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...

