"""Agent state: the blackboard the agent reasons over.

Everything the agent believes about the current run lives here as
*machine-readable* facts, not prose. That is what makes self-decision
possible: the decision engine reads :attr:`AgentState.facts` and
:attr:`AgentState.issues`, and the verifier writes back into them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from splicegaip.tools.context import RunContext


# --------------------------------------------------------------------------
# Issues
# --------------------------------------------------------------------------

BLOCKER = "blocker"
WARNING = "warning"
INFO = "info"

_SEVERITY_ORDER = {BLOCKER: 0, WARNING: 1, INFO: 2}


@dataclass(frozen=True)
class Issue:
    """A problem the verifier found in the current state."""

    code: str
    severity: str
    message: str
    suggestion: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class StepRecord:
    """One executed action (the agent's decision trace)."""

    index: int
    action: str
    args: dict[str, Any]
    status: str
    message: str
    rationale: str
    source: str
    seconds: float
    issues: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "action": self.action,
            "args": dict(self.args),
            "status": self.status,
            "message": self.message[:600],
            "rationale": self.rationale,
            "source": self.source,
            "seconds": round(self.seconds, 3),
            "issues": list(self.issues),
        }


# --------------------------------------------------------------------------
# Goal / acceptance criteria
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Criterion:
    """One machine-checkable acceptance criterion."""

    code: str
    description: str
    check: Callable[["AgentState"], bool]

    def satisfied(self, state: "AgentState") -> bool:
        try:
            return bool(self.check(state))
        except Exception:  # noqa: BLE001 - a broken check must not stall the run
            return False


def default_criteria() -> list[Criterion]:
    """What 'a complete splicing analysis' means, checkable by machine."""
    return [
        Criterion(
            "profiled",
            "Dataset profiled (size, missingness, quality known)",
            lambda s: bool(s.facts.get("profiled")),
        ),
        Criterion(
            "filtered",
            "Significance filtering executed",
            lambda s: bool(s.facts.get("filtered")),
        ),
        Criterion(
            "ranked",
            "Candidates ranked (or ranking proven impossible)",
            lambda s: bool(s.facts.get("ranked"))
            or any(
                item.get("code") == "no_significant_events"
                for item in s.facts.get("accepted_limitations", [])
            ),
        ),
        Criterion(
            "figures",
            "Figure set generated",
            lambda s: int(s.facts.get("figures", 0)) > 0,
        ),
        Criterion(
            "interpreted",
            "Biological interpretation produced",
            lambda s: bool(s.facts.get("interpreted")),
        ),
        Criterion(
            "reported",
            "Report written",
            lambda s: bool(s.facts.get("reported")),
        ),
    ]


@dataclass
class Goal:
    """The analysis goal plus its acceptance criteria."""

    analysis_type: str
    description: str
    criteria: list[Criterion] = field(default_factory=default_criteria)

    def evaluate(self, state: "AgentState") -> tuple[bool, list[str]]:
        """Return (satisfied, unmet criterion codes)."""
        unmet = [item.code for item in self.criteria if not item.satisfied(state)]
        return (not unmet), unmet

    def as_dict(self) -> dict[str, Any]:
        return {
            "analysis_type": self.analysis_type,
            "description": self.description,
            "criteria": [
                {"code": item.code, "description": item.description} for item in self.criteria
            ],
        }


# --------------------------------------------------------------------------
# Agent state
# --------------------------------------------------------------------------


@dataclass
class AgentState:
    """Blackboard shared by the decision engine, verifier and executor."""

    context: RunContext
    goal: Goal
    #: Numeric/boolean facts derived from the run context after each action.
    facts: dict[str, Any] = field(default_factory=dict)
    #: Data profile produced by :func:`profile_dataset`.
    profile: dict[str, Any] = field(default_factory=dict)
    #: Adaptive analysis parameters the agent chose (FDR, dPSI, top-N...).
    params: dict[str, Any] = field(default_factory=dict)
    #: Current open issues (rewritten by the verifier on every iteration).
    issues: list[Issue] = field(default_factory=list)
    #: Executed steps, in order.
    steps: list[StepRecord] = field(default_factory=list)
    #: How many times each action has been executed.
    action_counts: dict[str, int] = field(default_factory=dict)
    iteration: int = 0
    #: Bridge to the async external skills (budgeted, timeout-guarded).
    bridge: Any | None = None

    # -- observation ------------------------------------------------------
    def observe(self) -> dict[str, Any]:
        """Refresh facts from the run context (the 'sense' phase)."""
        context = self.context
        facts = self.facts
        facts["events_total"] = len(context.dataset.events)
        facts["significant"] = len(context.significant_events)
        facts["has_significant"] = len(context.significant_events) > 0
        facts["candidates"] = len(context.candidates)
        facts["enriched_terms"] = len(context.enrichment)
        facts["figures"] = len(context.figures)
        facts["evidence_genes"] = sum(1 for entries in context.evidence.values() if entries)
        facts["evidence_targets"] = len(context.evidence)
        facts["samples"] = len(context.dataset.samples)
        facts["groups"] = len(context.dataset.groups)
        facts["has_annotation"] = bool(context.dataset.annotation)
        facts["has_de_table"] = bool(context.dataset.de_genes)
        facts["reported"] = bool(context.report_paths)
        facts["profiled"] = bool(self.profile)
        facts["filtered"] = context.filter_report is not None
        facts["ranked"] = bool(context.candidates)
        facts["enriched"] = bool(context.filter_report is not None and context.enrichment) or (
            not context.dataset.annotation and context.filter_report is not None
        )
        facts["figures_done"] = bool(context.figures)
        facts["evidence_done"] = bool(context.evidence)
        facts["interpreted"] = any(
            step.action == "interpret_candidates" and step.status == "ok" for step in self.steps
        )
        return facts

    # -- helpers ----------------------------------------------------------
    def blockers(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == BLOCKER]

    def has_issue(self, code: str) -> bool:
        return any(issue.code == code for issue in self.issues)

    def resolve_issue(self, code: str) -> None:
        self.issues = [issue for issue in self.issues if issue.code != code]

    def note_action(self, action: str) -> None:
        self.action_counts[action] = self.action_counts.get(action, 0) + 1

    def count_of(self, action: str) -> int:
        return self.action_counts.get(action, 0)

    def sorted_issues(self) -> list[Issue]:
        return sorted(self.issues, key=lambda item: _SEVERITY_ORDER.get(item.severity, 3))

    def snapshot(self) -> dict[str, Any]:
        """Compact view handed to the decision engine (and to the LLM)."""
        return {
            "iteration": self.iteration,
            "goal": self.goal.description,
            "facts": dict(self.facts),
            "profile": {
                key: self.profile[key]
                for key in (
                    "event_count",
                    "fdr_coverage",
                    "delta_psi_coverage",
                    "median_support_reads",
                    "groups",
                    "flags",
                )
                if key in self.profile
            },
            "params": dict(self.params),
            "issues": [issue.as_dict() for issue in self.sorted_issues()],
            "done_actions": sorted(
                step.action for step in self.steps if step.status in {"ok", "skipped"}
            ),
            "action_counts": dict(self.action_counts),
        }


def start_timer() -> Callable[[], float]:
    """Return a callable giving elapsed seconds since its creation."""
    started = time.monotonic()
    return lambda: time.monotonic() - started
