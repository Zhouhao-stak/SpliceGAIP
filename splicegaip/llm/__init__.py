"""LLM layer: OpenAI-compatible model clients for the agent team.

Two implementations share the AutoGen ``ChatCompletionClient`` interface:

* :class:`OpenAICompatibleClient` — real LLM calls (configured through
  ``MODEL_API_BASE_URL`` / ``MODEL_API_KEY`` / ``MODEL_NAME``);
* :class:`splicegaip.llm.fallback.DeterministicClient` — scripted,
  deterministic responses used when no API key is configured, so the
  whole multi-agent pipeline still runs end to end.
"""

from splicegaip.llm.client import (
    build_model_client,
    describe_llm_mode,
)

__all__ = ["build_model_client", "describe_llm_mode"]
