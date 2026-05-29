import httpx

from app.config import Settings
from app.llm.interface import LLMClient
from app.tools.qwen_client import QwenClient


def build_llm_client(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> LLMClient:
    return QwenClient(settings, transport=transport)

