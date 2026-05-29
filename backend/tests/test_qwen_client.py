import json
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.tools.qwen_client import QwenClient


@pytest.mark.asyncio
async def test_chat_json_uses_fallback_without_key(tmp_path: Path) -> None:
    settings = Settings(dashscope_api_key="", data_dir=tmp_path)
    result = await QwenClient(settings).chat_json("system", "user", {"ok": False}, run_id="run_test")

    assert result == {"ok": False}
    log_path = tmp_path / "outputs" / "llm_calls" / "run_test.jsonl"
    assert log_path.exists()
    assert json.loads(log_path.read_text().splitlines()[0])["status"] == "fallback"


@pytest.mark.asyncio
async def test_chat_json_parses_mocked_bailian_response(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/compatible-mode/v1/chat/completions"
        assert request.headers["authorization"].startswith("Bearer ")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "```json\n{\"ok\": true}\n```"}}],
                "usage": {"total_tokens": 12},
            },
        )

    settings = Settings(
        dashscope_api_key="test-key",
        dashscope_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        data_dir=tmp_path,
    )
    client = QwenClient(settings, transport=httpx.MockTransport(handler))

    result = await client.chat_json("system", "user", {"ok": False}, run_id="run_test", agent="planner")

    assert result == {"ok": True}
    log_line = json.loads((tmp_path / "outputs" / "llm_calls" / "run_test.jsonl").read_text().splitlines()[0])
    assert log_line["status"] == "success"
    assert log_line["token_usage"]["total_tokens"] == 12


@pytest.mark.asyncio
async def test_chat_text_returns_mocked_content(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "TrustSci Qwen connection ok."}}]})

    settings = Settings(dashscope_api_key="test-key", data_dir=tmp_path)
    client = QwenClient(settings, transport=httpx.MockTransport(handler))

    result = await client.chat_text("system", "user", "fallback")

    assert result == "TrustSci Qwen connection ok."

