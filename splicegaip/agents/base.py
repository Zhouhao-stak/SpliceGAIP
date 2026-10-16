"""Agent construction.

Agents are AutoGen ``AssistantAgent`` instances assembled from the
system prompts and the tool set, mirroring BioGAIP's YAML-driven agent
assembly (``load_agents``) with the three-agent SpliceGAIP roster.
"""

from __future__ import annotations

from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient

from splicegaip.agents.prompts import (
    ANALYST_SYSTEM_MESSAGE,
    INTERPRETER_SYSTEM_MESSAGE,
    PLANNER_SYSTEM_MESSAGE,
)

AGENT_NAMES = ("bio_planner", "bio_analyst", "bio_interpreter")


def build_agents(
    *,
    planner_client: ChatCompletionClient,
    analyst_client: ChatCompletionClient,
    interpreter_client: ChatCompletionClient,
    tools: dict[str, Any],
    analyst_tools: tuple[str, ...] = (
        "summarize_dataset",
        "filter_significant_events",
        "rank_candidates",
        "run_enrichment",
        "generate_figures",
    ),
    interpreter_tools: tuple[str, ...] = (
        "collect_literature_evidence",
        "interpret_candidates",
        "generate_report",
    ),
) -> dict[str, AssistantAgent]:
    """Build the three core agents with their tool subsets."""
    planner = AssistantAgent(
        name="bio_planner",
        model_client=planner_client,
        description="Planner agent: converts the user's research objective into a structured analysis workflow.",
        system_message=PLANNER_SYSTEM_MESSAGE,
    )
    analyst = AssistantAgent(
        name="bio_analyst",
        model_client=analyst_client,
        description="Analyst agent: filters, ranks and enriches AS events and generates figures.",
        system_message=ANALYST_SYSTEM_MESSAGE,
        tools=[tools[name] for name in analyst_tools],
        # One tool call per turn: the next model call returns the next
        # scripted tool call, which is what the deterministic policy and
        # the selector speaker order expect.
        reflect_on_tool_use=False,
    )
    interpreter = AssistantAgent(
        name="bio_interpreter",
        model_client=interpreter_client,
        description="Interpreter agent: collects literature evidence, interprets results and writes the report.",
        system_message=INTERPRETER_SYSTEM_MESSAGE,
        tools=[tools[name] for name in interpreter_tools],
        reflect_on_tool_use=False,
    )
    return {"bio_planner": planner, "bio_analyst": analyst, "bio_interpreter": interpreter}
