"""Autonomous agent core for SpliceGAIP.

This package turns the scripted multi-agent pipeline into a real
self-deciding agent: it observes the dataset, decides the next action from
what it just learned, verifies every result, reflects on problems and
re-plans within a budget.

Public entry point: :func:`splicegaip.agent.loop.run_autonomous`.
"""

from __future__ import annotations

from .loop import AgentRunResult, AutonomousAgent, run_autonomous

__all__ = ["run_autonomous", "AutonomousAgent", "AgentRunResult"]
