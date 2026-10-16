"""Model client construction.

When the environment provides ``MODEL_API_BASE_URL`` and ``MODEL_API_KEY``
the agents run on a real OpenAI-compatible endpoint; otherwise the
deterministic fallback client is used. This keeps Phase 1 fully
runnable offline while remaining a genuine multi-agent system.

Vendor specifics
----------------
"OpenAI-compatible" is not the same as "identical". This module knows the
few differences that actually break a run and keeps them in one place:

DeepSeek (``https://api.deepseek.com``, model ``deepseek-flash``)
    Thinking mode is **on by default at effort ``high``**. Two consequences
    matter here:

    * thinking mode ignores ``temperature`` / ``presence_penalty`` /
      ``frequency_penalty`` — so they are simply not sent when thinking is
      enabled, instead of being silently ignored (or rejected) upstream;
    * when a request carries ``tools``, the API requires every assistant
      turn to echo ``reasoning_content`` back, otherwise it answers ``400``.
      AutoGen does not currently round-trip that field, so every call that
      may carry tools disables thinking (the agent team always carries
      tools; the enrichment layer never does).

    ``MODEL_THINKING=enabled|disabled|auto`` and
    ``MODEL_REASONING_EFFORT=low|medium|high|...`` override the default.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from autogen_core.models import ChatCompletionClient

from splicegaip.config import Settings

#: Endpoints this module knows how to special-case.
KNOWN_PROVIDERS: tuple[str, ...] = ("deepseek", "openai", "moonshot", "dashscope", "generic")

#: Reasoning efforts accepted by the vendors that expose a thinking mode.
REASONING_EFFORTS: tuple[str, ...] = ("minimal", "low", "medium", "high", "xhigh", "max")

_HOST_HINTS: tuple[tuple[str, str], ...] = (
    ("api.deepseek.com", "deepseek"),
    ("deepseek.com", "deepseek"),
    ("api.openai.com", "openai"),
    ("openai.azure.com", "openai"),
    ("api.moonshot.cn", "moonshot"),
    ("moonshot.cn", "moonshot"),
    ("dashscope.aliyuncs.com", "dashscope"),
    ("dashscope.aliyun.com", "dashscope"),
    ("bigmodel.cn", "generic"),
)

_MODEL_HINTS: tuple[tuple[str, str], ...] = (
    ("deepseek", "deepseek"),
    ("gpt-", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
    ("moonshot", "moonshot"),
    ("kimi", "moonshot"),
    ("qwen", "dashscope"),
)


def detect_provider(settings: Settings) -> str:
    """Return the endpoint family for ``settings``.

    Resolution order: explicit ``MODEL_PROVIDER`` → host of ``base_url`` →
    model-name prefix. Unknown combinations yield ``"generic"``, which
    means "send nothing vendor-specific" (the safe default: it is what the
    platform did before this module existed).
    """
    configured = str(getattr(settings.llm, "provider", "auto") or "auto").strip().lower()
    if configured in KNOWN_PROVIDERS:
        return configured

    host = (urlparse(settings.llm.base_url or "").hostname or "").lower()
    for hint, provider in _HOST_HINTS:
        if host == hint or host.endswith("." + hint):
            return provider

    model = (settings.llm.model or "").lower()
    for hint, provider in _MODEL_HINTS:
        if model.startswith(hint):
            return provider
    return "generic"


def _normalised_thinking(raw: str) -> str:
    value = str(raw or "auto").strip().lower()
    if value in {"enabled", "enable", "on", "true", "1", "yes"}:
        return "enabled"
    if value in {"disabled", "disable", "off", "false", "0", "no"}:
        return "disabled"
    return "auto"


def resolve_thinking(settings: Settings, *, tools_expected: bool = True) -> str:
    """Thinking state ("enabled" / "disabled" / "") for one request kind.

    ``""`` means "not applicable to this vendor" and nothing is sent.
    ``tools_expected`` marks call sites where AutoGen may attach tools:
    those must never think on DeepSeek (see the module docstring).
    """
    explicit = _normalised_thinking(getattr(settings.llm, "thinking", "auto"))
    if explicit in {"enabled", "disabled"}:
        return explicit
    if detect_provider(settings) != "deepseek":
        return ""
    return "disabled" if tools_expected else "enabled"


def resolve_reasoning_effort(settings: Settings) -> str:
    """Validated reasoning effort, or ``""`` to use the vendor default."""
    value = str(getattr(settings.llm, "reasoning_effort", "") or "").strip().lower()
    return value if value in REASONING_EFFORTS else ""


def provider_extra_body(settings: Settings, *, tools_expected: bool = True) -> dict[str, Any]:
    """Vendor-specific request body overrides for this endpoint."""
    body: dict[str, Any] = {}
    if detect_provider(settings) != "deepseek":
        return body
    state = resolve_thinking(settings, tools_expected=tools_expected)
    if state:
        body["thinking"] = {"type": state}
        effort = resolve_reasoning_effort(settings)
        if effort and state == "enabled":
            body["reasoning_effort"] = effort
    return body


def effective_temperature(settings: Settings, *, tools_expected: bool = True) -> float | None:
    """Sampling temperature to send, or ``None`` when it must be omitted.

    DeepSeek's thinking mode rejects the sampling parameters, so a thinking
    request is sent without them rather than gambling on them being ignored.
    """
    if detect_provider(settings) != "deepseek":
        return float(settings.llm.temperature or 0.0)
    if resolve_thinking(settings, tools_expected=tools_expected) == "enabled":
        return None
    return float(settings.llm.temperature or 0.0)


def build_model_client(
    settings: Settings,
    *,
    model: str | None = None,
    tools_expected: bool = True,
) -> ChatCompletionClient:
    """Build a model client for an agent.

    :param settings: platform settings (LLM block).
    :param model: optional per-agent model override.
    :param tools_expected: whether this client may issue tool-calling
        requests. AutoGen's team agents do; the enrichment layer does not,
        and that difference decides whether thinking mode is safe.
    """
    llm = settings.llm
    if not llm.configured:
        raise ValueError(
            "No LLM configured (MODEL_API_BASE_URL / MODEL_API_KEY missing). "
            "Use build_deterministic_client() for offline runs."
        )
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    model_name = model or llm.model
    if not model_name:
        raise ValueError("MODEL_NAME is not set; cannot build the model client.")
    extra_body = provider_extra_body(settings, tools_expected=tools_expected)
    kwargs: dict[str, Any] = {}
    if extra_body:
        # Accepted by AutoGen's create_args filter, and merged into the JSON
        # body by the OpenAI SDK — this is how the thinking toggle (and any
        # future vendor knob) reaches the endpoint without forking the client.
        kwargs["extra_body"] = extra_body
    return OpenAIChatCompletionClient(
        model=model_name,
        base_url=llm.base_url,
        api_key=llm.api_key,
        timeout=llm.timeout_seconds,
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
            "structured_output": True,
            "multiple_system_messages": True,
        },
        **kwargs,
    )


def describe_llm_mode(settings: Settings) -> str:
    """Human-readable description of the active model mode."""
    if not settings.llm.configured:
        return "Deterministic mode: no LLM credentials configured; agents run the offline policy."
    provider = detect_provider(settings)
    detail = f"{settings.llm.model or '(default)'} via {settings.llm.base_url} ({provider})"
    thinking = resolve_thinking(settings, tools_expected=False)
    if provider == "deepseek" and thinking:
        effort = resolve_reasoning_effort(settings) or "vendor default"
        detail += f"; thinking={thinking} (effort={effort})"
    return f"LLM mode: {detail}"
