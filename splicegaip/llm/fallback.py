"""Deterministic (offline) model client.

Implements the AutoGen ``ChatCompletionClient`` interface with a
queue-replay policy: the deterministic analysis policy pre-computes the
full response script for each agent (plan text, tool calls with concrete
arguments, final summaries), and this client replays it through the real
AutoGen tool-calling machinery.

Consequences:

* the multi-agent team, tool execution and termination protocol are the
  same code paths as in LLM mode;
* the pipeline cannot loop forever (queues drain, then the client
  returns the final message containing the termination token);
* switching to a real LLM requires no code change — only credentials.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import AsyncGenerator, Sequence
from typing import Any, Callable

from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelCapabilities,
    ModelInfo,
    RequestUsage,
)

#: Token that terminates the team run (TextMentionTermination).
TERMINATION_TOKEN = "SPLICEGAIP_DONE"

_ZERO_USAGE = RequestUsage(prompt_tokens=0, completion_tokens=0)


def _text_result(text: str) -> CreateResult:
    return CreateResult(
        finish_reason="stop",
        content=text,
        usage=_ZERO_USAGE,
        cached=False,
    )


def _tool_result(call_id: str, name: str, arguments: dict[str, Any]) -> CreateResult:
    return CreateResult(
        finish_reason="function_calls",
        content=[{"id": call_id, "name": name, "arguments": json.dumps(arguments)}],
        usage=_ZERO_USAGE,
        cached=False,
    )


class DeterministicClient(ChatCompletionClient):
    """Queue-replay model client for one agent."""

    def __init__(
        self,
        agent_name: str,
        script: Sequence[dict[str, Any]] | None = None,
        finalizer: Callable[[], str] | None = None,
    ) -> None:
        self._agent_name = agent_name
        self._queue: deque[dict[str, Any]] = deque(script or [])
        self._finalizer = finalizer
        self._call_count = 0

    # -- scripting --------------------------------------------------------
    def enqueue(self, item: dict[str, Any]) -> None:
        """Append a scripted response (``{"text": ...}`` or ``{"tool": name, "args": {...}}``)."""
        self._queue.append(item)

    def set_finalizer(self, finalizer: Callable[[], str]) -> None:
        self._finalizer = finalizer

    # -- ChatCompletionClient interface -----------------------------------
    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(vision=False, function_calling=True, json_output=True)

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="deterministic",
            structured_output=True,
            multiple_system_messages=True,
        )

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        tool_choice: Any = None,
        **kwargs: Any,
    ) -> CreateResult:
        self._call_count += 1
        if self._queue:
            item = self._queue.popleft()
            if "tool" in item:
                return _tool_result(
                    call_id=f"det-{self._agent_name}-{self._call_count}",
                    name=str(item["tool"]),
                    arguments=dict(item.get("args", {})),
                )
            return _text_result(str(item.get("text", "")))
        if self._finalizer is not None:
            return _text_result(self._finalizer())
        return _text_result(f"{self._agent_name} finished. {TERMINATION_TOKEN}")

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        **kwargs: Any,
    ) -> AsyncGenerator[str | CreateResult, None]:
        yield await self.create(messages, tools=tools, **kwargs)

    async def close(self) -> None:
        return None

    def actual_usage(self) -> RequestUsage:
        return _ZERO_USAGE

    def total_usage(self) -> RequestUsage:
        return _ZERO_USAGE

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] = ()) -> int:
        return 0

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] = ()) -> int:
        return 100000


class DeterministicSelectorClient(ChatCompletionClient):
    """Selector model client that replays a planned speaker order."""

    def __init__(self, speaker_order: Sequence[str], participants: Sequence[str]) -> None:
        self._order = deque(speaker_order)
        self._participants = list(participants)

    def _next_speaker(self) -> str:
        while self._order:
            candidate = self._order.popleft()
            if candidate in self._participants:
                return candidate
        # Fall back to the interpreter (it holds the termination token).
        return self._participants[-1]

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(vision=False, function_calling=True, json_output=True)

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="deterministic-selector",
            structured_output=True,
            multiple_system_messages=True,
        )

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        tool_choice: Any = None,
        **kwargs: Any,
    ) -> CreateResult:
        speaker = self._next_speaker()
        return _text_result(f"The next agent to perform the task is {speaker}.")

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] = (),
        **kwargs: Any,
    ) -> AsyncGenerator[str | CreateResult, None]:
        yield await self.create(messages, tools=tools, **kwargs)

    async def close(self) -> None:
        return None

    def actual_usage(self) -> RequestUsage:
        return _ZERO_USAGE

    def total_usage(self) -> RequestUsage:
        return _ZERO_USAGE

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] = ()) -> int:
        return 0

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] = ()) -> int:
        return 100000
