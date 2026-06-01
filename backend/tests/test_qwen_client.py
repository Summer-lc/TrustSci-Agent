import json
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.llm.interface import LLMRequest, LLMResponseFormat
from app.tools.qwen_client import QwenClient
from app.tools.llm_logger import read_llm_logs


@pytest.mark.asyncio
async def test_chat_json_uses_fallback_without_key(tmp_path: Path) -> None:
    settings = Settings(dashscope_api_key="", data_dir=tmp_path)
    result = await QwenClient(settings).chat_json("system", "user", {"ok": False}, run_id="run_test")

    assert result == {"ok": False}
    log_path = tmp_path / "outputs" / "llm_calls" / "run_test.jsonl"
    assert log_path.exists()
    log_line = json.loads(log_path.read_text().splitlines()[0])
    assert log_line["status"] == "fallback"
    assert log_line["system_prompt"] == "system"
    assert log_line["user_prompt"] == "user"
    assert log_line["response"] == {"ok": False}
    assert log_line["model"] == settings.qwen_model
    assert log_line["token_usage"] == {}
    assert log_line["started_at"]
    assert log_line["finished_at"]
    assert isinstance(log_line["duration_ms"], int)


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
    assert log_line["system_prompt"] == "system"
    assert log_line["user_prompt"] == "user"
    assert log_line["response"] == {"ok": True}
    assert log_line["model"] == settings.qwen_model
    assert log_line["provider"] == "bailian-qwen"
    assert log_line["started_at"]
    assert log_line["finished_at"]
    assert isinstance(log_line["duration_ms"], int)


@pytest.mark.asyncio
async def test_chat_text_returns_mocked_content(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "TrustSci Qwen connection ok."}}]})

    settings = Settings(dashscope_api_key="test-key", data_dir=tmp_path)
    client = QwenClient(settings, transport=httpx.MockTransport(handler))

    result = await client.chat_text("system", "user", "fallback")

    assert result == "TrustSci Qwen connection ok."


@pytest.mark.asyncio
async def test_complete_normalizes_json_fallback(tmp_path: Path) -> None:
    settings = Settings(dashscope_api_key="", data_dir=tmp_path)
    client = QwenClient(settings)

    response = await client.complete(
        LLMRequest(
            system="system",
            user="user",
            fallback="offline",
            response_format=LLMResponseFormat.json,
            run_id="run_test",
        )
    )

    assert response.content == {"value": "offline"}
    assert response.fallback_used is True


@pytest.mark.asyncio
async def test_complete_writes_readable_llm_call_log(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "{\"ok\": true}"}}],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 3,
                    "total_tokens": 8,
                },
            },
        )

    settings = Settings(dashscope_api_key="test-key", data_dir=tmp_path, qwen_model="qwen-test")
    client = QwenClient(settings, transport=httpx.MockTransport(handler))

    response = await client.complete(
        LLMRequest(
            system="Return JSON only.",
            user="Plan a scientific workflow.",
            fallback={"ok": False},
            run_id="run_log_contract",
            agent="planner",
        )
    )

    logs = read_llm_logs(tmp_path, "run_log_contract")
    assert response.content == {"ok": True}
    assert len(logs) == 1
    assert logs[0]["agent"] == "planner"
    assert logs[0]["model"] == "qwen-test"
    assert logs[0]["system_prompt"] == "Return JSON only."
    assert logs[0]["user_prompt"] == "Plan a scientific workflow."
    assert logs[0]["response"] == {"ok": True}
    assert logs[0]["token_usage"] == {
        "prompt_tokens": 5,
        "completion_tokens": 3,
        "total_tokens": 8,
    }
    assert logs[0]["started_at"]
    assert logs[0]["finished_at"]
    assert isinstance(logs[0]["duration_ms"], int)
