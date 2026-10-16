"""Team assembly and execution.

Assembles the AutoGen ``SelectorGroupChat`` for the three core agents and
runs the analysis task. The same code path runs in LLM mode (real model
clients) and in deterministic mode (scripted clients), differing only in
the model clients injected.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat

from splicegaip.agents.base import build_agents
from splicegaip.agents.policy import build_deterministic_clients, speaker_order
from splicegaip.agents.prompts import SELECTOR_PROMPT
from splicegaip.llm.client import build_model_client
from splicegaip.llm.fallback import TERMINATION_TOKEN, DeterministicSelectorClient
from splicegaip.tools import build_tools
from splicegaip.tools.context import RunContext

#: Safety cap on team turns (protects against runaway loops).
MAX_TURNS = 40


@dataclass
class TeamRunResult:
    """Outcome of one team run."""

    messages: list[dict[str, str]] = field(default_factory=list)
    tool_calls: list[dict[str, str]] = field(default_factory=list)
    stopped_reason: str = "completed"
    elapsed_seconds: float = 0.0
    mode: str = "deterministic"

    def as_dict(self) -> dict[str, Any]:
        return {
            "messages": self.messages,
            "tool_calls": self.tool_calls,
            "stopped_reason": self.stopped_reason,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "mode": self.mode,
        }


def _task_message(context: RunContext) -> str:
    """The initial task message handed to the team."""
    import json

    dataset = context.dataset
    groups = dataset.groups
    group_text = ", ".join(f"{group} ({len(ids)} samples)" for group, ids in groups.items())
    message = (
        f"User query: {context.query}\n\n"
        f"Dataset: {dataset.name} (format: {dataset.source_format}, "
        f"{len(dataset.events)} AS events, samples: {group_text or 'unspecified'}).\n"
        f"Input directory: {dataset.source_dir}\n"
        f"Output directory: {context.output_dir}\n\n"
        "Execute the full analysis workflow and produce the final report."
    )
    # Pre-analysis intent understanding (model-based when configured) is
    # handed to the planner so its plan matches the user's real objective.
    understanding = getattr(context, "understanding", None)
    if isinstance(understanding, dict) and understanding:
        message += (
            "\n\nStructured intent resolved before the run (advisory, do not treat as data):\n"
            + json.dumps(understanding, ensure_ascii=False, indent=2)
        )
    return message


def run_team(context: RunContext) -> TeamRunResult:
    """Build and run the agent team for ``context`` (synchronous entry)."""
    return asyncio.run(_run_team_async(context))


async def _run_team_async(context: RunContext) -> TeamRunResult:
    started = time.monotonic()
    tools = build_tools(context)
    mode = "deterministic"
    planner_client: Any = None
    analyst_client: Any = None
    interpreter_client: Any = None
    selector_client: Any = None
    if context.settings.llm.configured:
        try:
            # ``tools_expected=True`` keeps vendor reasoning modes that break
            # tool calling switched off (see splicegaip.llm.client).
            planner_client = build_model_client(context.settings, tools_expected=True)
            analyst_client = build_model_client(
                context.settings, model=context.settings.llm.analyst_model, tools_expected=True
            )
            interpreter_client = build_model_client(
                context.settings, model=context.settings.llm.model, tools_expected=True
            )
            selector_client = build_model_client(context.settings, tools_expected=True)
            mode = "llm"
        except Exception as error:  # noqa: BLE001 - fall back to deterministic mode
            context.log(
                "system",
                "llm_fallback",
                "warning",
                f"LLM client failed ({error}); using deterministic mode.",
            )
            planner_client = analyst_client = interpreter_client = selector_client = None
    if mode == "deterministic":
        planner_client, analyst_client, interpreter_client = build_deterministic_clients(context)
        selector_client = DeterministicSelectorClient(
            speaker_order(), ("bio_planner", "bio_analyst", "bio_interpreter")
        )

    agents = build_agents(
        planner_client=planner_client,
        analyst_client=analyst_client,
        interpreter_client=interpreter_client,
        tools=tools,
    )
    team = SelectorGroupChat(
        list(agents.values()),
        model_client=selector_client,
        termination_condition=TextMentionTermination(TERMINATION_TOKEN),
        selector_prompt=SELECTOR_PROMPT,
        allow_repeated_speaker=True,
    )

    result = TeamRunResult(mode=mode)
    turn = 0
    try:
        async for event in team.run_stream(task=_task_message(context)):
            turn += 1
            _record_event(event, result)
            if turn >= MAX_TURNS:
                result.stopped_reason = f"max_turns ({MAX_TURNS}) reached"
                break
    except Exception as error:  # noqa: BLE001 - report but do not crash the run
        result.stopped_reason = f"error: {error}"
        context.log("system", "team_run", "error", str(error))
    finally:
        result.elapsed_seconds = time.monotonic() - started
        _persist_planner_plan(context, result)
        try:
            await team.close()
        except Exception:  # noqa: BLE001
            pass
    return result


def _persist_planner_plan(context: RunContext, result: TeamRunResult) -> None:
    """Save the planner's plan JSON into the analysis memory."""
    import json

    for message in result.messages:
        if message["source"] != "bio_planner":
            continue
        try:
            plan = json.loads(message["content"])
        except (ValueError, TypeError):
            continue
        if isinstance(plan, dict):
            context.memory.save_plan(context.project_id, plan)
            context.plan = plan
            context.log("bio_planner", "save_plan", "ok", str(plan.get("goal", "")))
            return


def _record_event(event: Any, result: TeamRunResult) -> None:
    """Convert AutoGen stream events into the run log."""
    from autogen_agentchat.base import Response
    from autogen_agentchat.messages import (
        TextMessage,
        ToolCallExecutionEvent,
        ToolCallRequestEvent,
    )

    if isinstance(event, Response):
        result.messages.append({"source": "final", "content": str(event.chat_message.content)})
    elif isinstance(event, ToolCallRequestEvent):
        for call in event.content:
            result.tool_calls.append(
                {"agent": str(event.source), "tool": call.name, "arguments": str(call.arguments)}
            )
    elif isinstance(event, ToolCallExecutionEvent):
        for call in event.content:
            result.tool_calls.append(
                {"agent": str(event.source), "tool": call.name, "result": str(call.content)[:500]}
            )
    elif isinstance(event, TextMessage):
        result.messages.append({"source": str(event.source), "content": str(event.content)})


def available_agent_names() -> tuple[str, ...]:
    return ("bio_planner", "bio_analyst", "bio_interpreter")
