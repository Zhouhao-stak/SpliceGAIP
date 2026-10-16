"""Reflection: turning a detected problem into a concrete next action.

This is the piece that was missing: previously the platform's critique was
prose that went straight into the report. Here every known issue code maps
to a *remediation* the agent can execute, with a retry cap so reflection can
never loop forever.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .state import AgentState

#: How many times one remediation may be attempted per run.
MAX_RETRIES: dict[str, int] = {
    "adapt_thresholds": 2,
    "filter_significant_events": 3,
    "generate_figures": 2,
    "collect_literature_evidence": 2,
    "rank_candidates": 2,
    "deep_dive_gene": 3,
    # Phase 2 actions: one attempt is enough (network calls are expensive).
    "test_hypothesis": 2,
    "annotate_genes": 1,
    "search_literature": 2,
    "enrich_pathways": 1,
    "interpret_splice_event": 1,
}


@dataclass(frozen=True)
class Remediation:
    """A concrete follow-up action proposed by the reflector."""

    action: str
    args: dict[str, Any]
    rationale: str
    #: Issue code this remediation addresses.
    addresses: str

    def as_tuple(self) -> tuple[str, dict[str, Any], str]:
        return self.action, dict(self.args), self.rationale


def _remedy_no_significant(state: AgentState) -> Remediation | None:
    if state.count_of("adapt_thresholds") >= MAX_RETRIES["adapt_thresholds"]:
        return None
    strategy = "exploratory"
    return Remediation(
        action="adapt_thresholds",
        args={"strategy": strategy},
        rationale=(
            "Zero significant events at the configured gates; relaxing them from the data "
            "distribution is the only way to produce a non-empty result."
        ),
        addresses="no_significant_events",
    )


def _remedy_no_candidates(state: AgentState) -> Remediation | None:
    if state.count_of("rank_candidates") >= MAX_RETRIES["rank_candidates"]:
        return None
    return Remediation(
        action="rank_candidates",
        args={},
        rationale="Significant events exist but ranking returned nothing; retry ranking.",
        addresses="no_candidates",
    )


def _remedy_too_many(state: AgentState) -> Remediation | None:
    if state.count_of("adapt_thresholds") >= MAX_RETRIES["adapt_thresholds"]:
        return None
    return Remediation(
        action="adapt_thresholds",
        args={"strategy": "strict"},
        rationale="Too many significant events to prioritize; tighten the gates to a workable set.",
        addresses="too_many_significant",
    )


def _remedy_few(state: AgentState) -> Remediation | None:
    if state.count_of("adapt_thresholds") >= MAX_RETRIES["adapt_thresholds"]:
        return None
    return Remediation(
        action="adapt_thresholds",
        args={"strategy": "exploratory"},
        rationale="Only a handful of significant events; try a slightly more exploratory gate.",
        addresses="few_significant_events",
    )


def _remedy_sparse_evidence(state: AgentState) -> Remediation | None:
    if state.count_of("collect_literature_evidence") >= MAX_RETRIES["collect_literature_evidence"]:
        return None
    return Remediation(
        action="collect_literature_evidence",
        args={"max_per_gene": 3},
        rationale="Evidence coverage is thin; retry with a larger per-gene limit.",
        addresses="sparse_evidence",
    )


def _remedy_figures(state: AgentState) -> Remediation | None:
    if state.count_of("generate_figures") >= MAX_RETRIES["generate_figures"]:
        return None
    return Remediation(
        action="generate_figures",
        args={},
        rationale="Figure generation produced nothing; retry once.",
        addresses="figures_missing",
    )


REMEDIATIONS: dict[str, Any] = {
    "no_significant_events": _remedy_no_significant,
    "no_candidates": _remedy_no_candidates,
    "too_many_significant": _remedy_too_many,
    "few_significant_events": _remedy_few,
    "sparse_evidence": _remedy_sparse_evidence,
    "figures_missing": _remedy_figures,
}


def remediate(code: str, state: AgentState) -> Remediation | None:
    """Propose a follow-up action for ``code``, or ``None`` to accept it."""
    handler = REMEDIATIONS.get(code)
    if handler is None:
        return None
    try:
        return handler(state)
    except Exception:  # noqa: BLE001 - reflection must never crash the loop
        return None


def reflect(state: AgentState) -> list[Remediation]:
    """Collect remediation proposals for every open issue."""
    proposals: list[Remediation] = []
    for issue in state.sorted_issues():
        remedy = remediate(issue.code, state)
        if remedy is not None:
            proposals.append(remedy)
    return proposals
