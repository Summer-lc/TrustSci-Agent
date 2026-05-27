import json
import time
from typing import Any
from uuid import uuid4

import httpx

from app.config import Settings
from app.schemas.common import utc_now
from app.schemas.llm import LLMCallLog
from app.tools.llm_logger import LLMLogger


class QwenClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
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
        call_id = f"llm_{uuid4().hex[:12]}"
        started = utc_now()
        started_monotonic = time.monotonic()
        if not self.settings.llm_enabled:
            self._log(
                LLMCallLog(
                    call_id=call_id,
                    run_id=run_id,
                    agent=agent,
                    model=self.settings.qwen_model,
                    llm_enabled=False,
                    status="fallback",
                    fallback_used=True,
                    started_at=started,
                    finished_at=utc_now(),
                    duration_ms=int((time.monotonic() - started_monotonic) * 1000),
                    system_prompt=system,
                    user_prompt=user,
                    response=fallback,
                )
            )
            return fallback

        payload = {
            "model": self.settings.qwen_model,
            "temperature": self.settings.qwen_temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.settings.dashscope_api_key}"}
        url = f"{self.settings.dashscope_base_url.rstrip('/')}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            response_json = response.json()
            content = response_json["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            self._log(
                LLMCallLog(
                    call_id=call_id,
                    run_id=run_id,
                    agent=agent,
                    model=self.settings.qwen_model,
                    llm_enabled=True,
                    status="success",
                    fallback_used=False,
                    started_at=started,
                    finished_at=utc_now(),
                    duration_ms=int((time.monotonic() - started_monotonic) * 1000),
                    system_prompt=system,
                    user_prompt=user,
                    response=parsed,
                    token_usage=response_json.get("usage") or {},
                )
            )
            return parsed
        except Exception as exc:
            self._log(
                LLMCallLog(
                    call_id=call_id,
                    run_id=run_id,
                    agent=agent,
                    model=self.settings.qwen_model,
                    llm_enabled=True,
                    status="error",
                    fallback_used=True,
                    started_at=started,
                    finished_at=utc_now(),
                    duration_ms=int((time.monotonic() - started_monotonic) * 1000),
                    system_prompt=system,
                    user_prompt=user,
                    response=fallback,
                    error=str(exc),
                )
            )
            return fallback

    def _log(self, log: LLMCallLog) -> None:
        self.logger.write(log)
