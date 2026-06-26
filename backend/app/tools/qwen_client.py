import asyncio
import json
import re
import time
from typing import Any
from uuid import uuid4

import httpx

from app.config import Settings
from app.llm.interface import LLMRequest, LLMResponse, LLMResponseFormat
from app.schemas.common import utc_now
from app.schemas.llm import LLMCallLog
from app.tools.llm_logger import LLMLogger


class QwenClient:
    """Bailian/DashScope OpenAI-compatible chat client.

    The client never stores API keys in logs. It records prompts, responses,
    token usage, latency, and fallback/error status for contest audit evidence.
    """

    provider = "bailian-qwen"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport
        self.logger = LLMLogger(settings.data_dir)

    async def chat_json(
        self,
        system: str,
        user: str,
        fallback: dict[str, Any],
        *,
        run_id: str | None = None,
        agent: str = "unknown",
    ) -> dict[str, Any]:
        result = await self._chat(
            system=system,
            user=user,
            fallback=fallback,
            run_id=run_id,
            agent=agent,
            response_format={"type": "json_object"},
            parser=_parse_json_content,
        )
        return result if isinstance(result, dict) else fallback

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if request.response_format == LLMResponseFormat.text:
            fallback = str(request.fallback)
            content = await self.chat_text(
                request.system,
                request.user,
                fallback,
                run_id=request.run_id,
                agent=request.agent,
            )
        else:
            fallback = (
                request.fallback
                if isinstance(request.fallback, dict)
                else {"value": request.fallback}
            )
            content = await self.chat_json(
                request.system,
                request.user,
                fallback,
                run_id=request.run_id,
                agent=request.agent,
            )
        return LLMResponse(
            content=content,
            provider=self.provider,
            model=self.settings.qwen_model,
            fallback_used=content == fallback,
        )

    async def chat_text(
        self,
        system: str,
        user: str,
        fallback: str,
        *,
        run_id: str | None = None,
        agent: str = "unknown",
    ) -> str:
        result = await self._chat(
            system=system,
            user=user,
            fallback=fallback,
            run_id=run_id,
            agent=agent,
            response_format=None,
            parser=lambda content: content.strip(),
        )
        return result if isinstance(result, str) else fallback

    async def ping(self) -> dict[str, Any]:
        if not self.settings.llm_enabled:
            return {
                "configured": False,
                "status": "not_configured",
                "model": self.settings.qwen_model,
                "message": "DASHSCOPE_API_KEY is not configured.",
            }
        try:
            text = await self.chat_text(
                "You are a connectivity checker. Reply with a short plain sentence.",
                "Say: TrustSci Qwen connection ok.",
                "fallback",
                agent="qwen_ping",
            )
            return {
                "configured": True,
                "status": "ok" if text != "fallback" else "fallback",
                "model": self.settings.qwen_model,
                "message": "Qwen API call completed.",
                "response_preview": text[:200],
            }
        except Exception as exc:
            return {
                "configured": True,
                "status": "error",
                "model": self.settings.qwen_model,
                "message": "Qwen API call failed.",
                "error": str(exc),
            }

    async def _chat(
        self,
        *,
        system: str,
        user: str,
        fallback: Any,
        run_id: str | None,
        agent: str,
        response_format: dict[str, str] | None,
        parser,
    ) -> Any:
        call_id = f"llm_{uuid4().hex[:12]}"
        started = utc_now()
        started_monotonic = time.monotonic()

        if not self.settings.llm_enabled:
            self._write_log(
                call_id=call_id,
                run_id=run_id,
                agent=agent,
                status="fallback",
                fallback_used=True,
                started=started,
                started_monotonic=started_monotonic,
                system=system,
                user=user,
                response=fallback,
            )
            return fallback

        try:
            response_json = await self._post_chat_completion(system, user, response_format)
            content = _extract_message_content(response_json)
            parsed = parser(content)
            self._write_log(
                call_id=call_id,
                run_id=run_id,
                agent=agent,
                status="success",
                fallback_used=False,
                started=started,
                started_monotonic=started_monotonic,
                system=system,
                user=user,
                response=parsed,
                token_usage=response_json.get("usage") or {},
            )
            return parsed
        except Exception as exc:
            self._write_log(
                call_id=call_id,
                run_id=run_id,
                agent=agent,
                status="error",
                fallback_used=True,
                started=started,
                started_monotonic=started_monotonic,
                system=system,
                user=user,
                response=fallback,
                error=_format_exception(exc),
            )
            return fallback

    async def _post_chat_completion(
        self,
        system: str,
        user: str,
        response_format: dict[str, str] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.settings.qwen_model,
            "temperature": self.settings.qwen_temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.dashscope_base_url.rstrip('/')}/chat/completions"
        last_error: Exception | None = None
        for attempt in range(self.settings.qwen_max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.qwen_timeout_seconds,
                    transport=self.transport,
                ) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    return response.json()
            except Exception as exc:
                last_error = exc
                if attempt >= self.settings.qwen_max_retries:
                    break
                await asyncio.sleep(min(0.5 * (attempt + 1), 2.0))
        if last_error is not None:
            raise last_error
        raise RuntimeError("Qwen request failed without an exception.")

    def _write_log(
        self,
        *,
        call_id: str,
        run_id: str | None,
        agent: str,
        status: str,
        fallback_used: bool,
        started,
        started_monotonic: float,
        system: str,
        user: str,
        response: Any,
        token_usage: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        self.logger.write(
            LLMCallLog(
                call_id=call_id,
                run_id=run_id,
                agent=agent,
                model=self.settings.qwen_model,
                llm_enabled=self.settings.llm_enabled,
                status=status,
                fallback_used=fallback_used,
                started_at=started,
                finished_at=utc_now(),
                duration_ms=int((time.monotonic() - started_monotonic) * 1000),
                system_prompt=system,
                user_prompt=user,
                response=response,
                token_usage=token_usage or {},
                error=error,
            )
        )


def _extract_message_content(response_json: dict[str, Any]) -> str:
    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Unexpected Qwen response shape: {response_json}") from exc
    if not isinstance(content, str):
        raise ValueError("Qwen response content is not a string.")
    return content


def _parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _format_exception(exc: Exception) -> str:
    detail = str(exc) or repr(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        response_text = exc.response.text[:1000] if exc.response is not None else ""
        return (
            f"{type(exc).__name__}: status={exc.response.status_code}; "
            f"message={detail}; response={response_text}"
        )
    if isinstance(exc, httpx.RequestError):
        return f"{type(exc).__name__}: {detail}; url={exc.request.url if exc.request else 'unknown'}"
    return f"{type(exc).__name__}: {detail}"
