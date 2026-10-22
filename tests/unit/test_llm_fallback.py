"""Tests for the offline deterministic model clients."""

import asyncio

from splicegaip.llm.fallback import (
    TERMINATION_TOKEN,
    DeterministicClient,
    DeterministicSelectorClient,
)


def test_deterministic_client_replays_text_tool_and_finalizer():
    async def scenario():
        client = DeterministicClient(
            "planner",
            [{"text": "plan"}, {"tool": "filter_events", "args": {"fdr": 0.05}}],
            finalizer=lambda: "summary",
        )
        first = await client.create([])
        second = await client.create([])
        third = await client.create([])
        stream = [item async for item in client.create_stream([])]
        return client, first, second, third, stream

    client, first, second, third, stream = asyncio.run(scenario())
    assert first.content == "plan"
    assert second.finish_reason == "function_calls"
    assert second.content[0].name == "filter_events"
    assert third.content == "summary"
    assert stream[0].content == "summary"
    assert client.count_tokens([]) == 0
    assert client.remaining_tokens([]) > 0


def test_deterministic_client_terminates_when_queue_is_empty():
    async def scenario():
        return await DeterministicClient("critic").create([])

    result = asyncio.run(scenario())
    assert TERMINATION_TOKEN in result.content


def test_selector_skips_unknown_speakers_and_falls_back_to_last_participant():
    async def scenario():
        client = DeterministicSelectorClient(["missing", "analyst"], ["analyst", "interpreter"])
        first = await client.create([])
        second = await client.create([])
        stream = [item async for item in client.create_stream([])]
        return first, second, stream

    first, second, stream = asyncio.run(scenario())
    assert "analyst" in first.content
    assert "interpreter" in second.content
    assert "interpreter" in stream[0].content
