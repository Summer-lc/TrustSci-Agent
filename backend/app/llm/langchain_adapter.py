"""LangChain compatibility adapter for the TrustSci-Agent LLMClient (Phase 2).

Wraps the existing ``LLMClient`` (e.g. ``QwenClient``) as a LangChain
``Runnable`` so agents can be expressed as LangChain LCEL chains
(``PromptTemplate | model | parser``) while preserving the ``LLMRequest``
contract and the ``data/outputs/llm_calls`` audit log.

The adapter does NOT replace ``QwenClient`` with a LangChain ``ChatModel``.
Every call still flows through ``LLMClient.complete(LLMRequest(...))``, so:

- ``LLMRequest.system / user / fallback / response_format / run_id / agent``
  are preserved exactly.
- ``QwenClient`` writes the same ``jsonl`` audit-log row (same fields, same
  per-run call count) as a direct ``complete()`` call.
- the ``llm_enabled`` / fallback / retry behavior is unchanged.

Usage (see ``PlannerAgent`` for a full example)::

    chain = (
        PROMPT
        | LLMClientRunnable(llm).bind(fallback=fallback, run_id=run.run_id, agent="planner")
        | SomeParser(fallback=fallback)
    )
    result = await chain.ainvoke(prompt_variables)

TODO(phase-2+): the same adapter can back ``ReportWriterAgent`` /
``ReportReviserAgent`` when they are migrated. Their prompt/structured-output
logic must not change report behavior, so they are intentionally left on the
direct ``self.llm.complete()`` path for now.
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.interface import LLMClient, LLMRequest, LLMResponseFormat


def build_agent_prompt(system_prompt: str) -> ChatPromptTemplate:
    """ChatPromptTemplate with a literal system message + a single ``{user_prompt}`` slot.

    The system prompt is a literal ``SystemMessage`` (not templated), so any
    ``{`` / ``}`` in it (e.g. the JSON-shape examples in agent SYSTEM_PROMPTs)
    are preserved verbatim and not interpreted as template variables. The user
    slot receives the agent's pre-built prompt string (often a ``json.dumps``
    payload), substituted literally so its braces are not re-interpreted.
    """
    return ChatPromptTemplate.from_messages(
        [SystemMessage(content=system_prompt), ("user", "{user_prompt}")]
    )


class FallbackParser(Runnable):
    """LangChain ``Runnable`` that normalizes LLM content, falling back on error.

    Wraps an agent's existing normalize callable (``content -> normalized`` so
    a malformed model output never crashes the run. ``fallback`` is the agent's
    *typed* fallback object (``list`` / ``ExperimentPlan`` / report / audit),
    NOT the ``LLMRequest`` fallback dict — the latter is bound separately on
    ``LLMClientRunnable`` for the audit log.
    """

    def __init__(self, normalize: Any, fallback: Any) -> None:
        super().__init__()
        self._normalize = normalize
        self.fallback = fallback

    def parse(self, content: Any) -> Any:
        try:
            return self._normalize(content)
        except Exception:
            return self.fallback

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return self.parse(input)

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return self.parse(input)


def _extract_prompt_text(prompt_value: Any) -> tuple[str, str]:
    """Return ``(system, user)`` text from a LangChain prompt value or string.

    Accepts a ``ChatPromptValue`` / ``StringPromptValue`` (from a
    ``ChatPromptTemplate``) or a plain string. System message content goes to
    ``system``; every other message's content is joined into ``user``.
    """
    if isinstance(prompt_value, str):
        return "", prompt_value
    to_messages = getattr(prompt_value, "to_messages", None)
    if to_messages is None:
        to_string = getattr(prompt_value, "to_string", None)
        return "", str(to_string()) if to_string else ""
    messages = list(to_messages())
    if not messages:
        return "", ""
    system = ""
    user_parts: list[str] = []
    for message in messages:
        msg_type = getattr(message, "type", "user")
        content = getattr(message, "content", "")
        if msg_type == "system":
            system = str(content)
        else:
            user_parts.append(str(content))
    return system, "\n".join(user_parts)


class LLMClientRunnable(Runnable):
    """LangChain ``Runnable`` that delegates to ``LLMClient.complete()``.

    Piped after a ``PromptTemplate``: the rendered prompt value becomes the
    ``system``/``user`` of an ``LLMRequest``. The bound kwargs
    (``fallback``, ``run_id``, ``agent``, ``response_format``) become the
    request metadata, so the audit-log row is identical to a direct
    ``LLMClient.complete()`` call.

    Async-only: the workflow is async, so ``invoke`` (sync) raises. Use
    ``ainvoke``.
    """

    def __init__(
        self,
        llm: LLMClient,
        response_format: LLMResponseFormat = LLMResponseFormat.json,
    ) -> None:
        super().__init__()
        self.llm = llm
        self.response_format = response_format

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        fallback = kwargs.get("fallback")
        run_id = kwargs.get("run_id")
        agent = kwargs.get("agent", "unknown")
        response_format = kwargs.get("response_format", self.response_format)
        system, user = _extract_prompt_text(input)
        request = LLMRequest(
            system=system,
            user=user,
            fallback=fallback,
            response_format=response_format,
            run_id=run_id,
            agent=agent,
        )
        response = await self.llm.complete(request)
        return response.content

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        raise NotImplementedError(
            "LLMClientRunnable is async-only; call ainvoke() (the workflow is async)."
        )
