"""Multi-turn follow-up: persist and resume the agent's decision state.

A full analysis ends with a serialisable snapshot of the agent's blackboard
(``facts`` / ``params`` / ``steps`` / ``goal``). A later *follow-up* query can
reload that snapshot and continue from where it stopped instead of re-running
the whole observation→decision→act loop. Only the new intent (e.g. "zoom into
gene TP53" or "keep only SE events") is executed as a short prefix of actions;
the normal loop then re-satisfies the tail criteria (interpret + report).

See :mod:`splicegaip.agent.loop` (``resuming`` / ``followup``) and
:func:`splicegaip.pipeline.resume_analysis`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .state import AgentState, Goal, Issue, StepRecord

STATE_FILE = "agent_state.json"

#: Canonical alternative-splicing event types the planner understands.
KNOWN_EVENT_TYPES = ("SE", "MXE", "RI", "A3SS", "A5SS")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_state(state: AgentState, project_dir: str | Path) -> Path:
    """Write the agent's decision state next to the report.

    The payload is plain JSON (``default=str`` guards against the occasional
    non-serialisable fact). Missing files are created; failures are reported as
    a returned ``Path`` only — callers should never crash on persistence.
    """
    project_dir = Path(project_dir)
    payload: dict[str, Any] = {
        "facts": state.facts,
        "params": state.params,
        "action_counts": state.action_counts,
        "iteration": state.iteration,
        "profile": state.profile,
        "goal": state.goal.as_dict(),
        "issues": [issue.as_dict() for issue in state.issues],
        "accepted_limitations": list(state.facts.get("accepted_limitations", [])),
        "steps": [step.as_dict() for step in state.steps],
    }
    path = project_dir / STATE_FILE
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def load_state(project_dir: str | Path, context: Any) -> AgentState | None:
    """Rebuild an :class:`AgentState` from a prior run.

    Returns ``None`` when no snapshot exists. The decision engine's lambda-based
    acceptance criteria cannot be serialised, so the goal is rebuilt with the
    default criteria set (the prior ``analysis_type`` / ``description`` are kept
    for traceability).
    """
    path = Path(project_dir) / STATE_FILE
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))

    goal_data = data.get("goal") or {}
    state = AgentState(
        context=context,
        goal=Goal(
            analysis_type=str(goal_data.get("analysis_type", "differential_AS")),
            description=str(goal_data.get("description", "")),
        ),
    )
    for key in ("facts", "params", "action_counts", "profile"):
        value = data.get(key)
        if isinstance(value, dict):
            setattr(state, key, dict(value))
    state.iteration = int(data.get("iteration", 0))
    state.issues = [
        Issue(
            code=str(issue.get("code", "")),
            severity=str(issue.get("severity", "info")),
            message=str(issue.get("message", "")),
            suggestion=str(issue.get("suggestion", "")),
        )
        for issue in data.get("issues", [])
        if isinstance(issue, dict)
    ]
    state.facts["accepted_limitations"] = list(data.get("accepted_limitations", []))
    for raw in data.get("steps", []):
        try:
            state.steps.append(
                StepRecord(
                    index=int(raw.get("index", 0)),
                    action=str(raw.get("action", "")),
                    args=raw.get("args") if isinstance(raw.get("args"), dict) else {},
                    status=str(raw.get("status", "ok")),
                    message=str(raw.get("message", "")),
                    rationale=str(raw.get("rationale", "")),
                    source=str(raw.get("source", "rule")),
                    seconds=float(raw.get("seconds", 0.0)),
                    issues=list(raw.get("issues") or []),
                )
            )
        except Exception:  # noqa: BLE001 - a corrupt step must not kill the resume
            continue
    return state


# ---------------------------------------------------------------------------
# Follow-up intent (rule-based, no LLM required)
# ---------------------------------------------------------------------------
def parse_followup(query: str, known_genes: list[str] | None = None) -> dict[str, Any]:
    """Turn a follow-up query into concrete planner instructions.

    Two patterns are recognised without any model call:

    * **gene focus** — "zoom into TP53", "look at CD44" → ``genes``
    * **event-type restriction** — "only SE events", "keep RI" → ``event_types``

    ``known_genes`` should be the candidate gene symbols from the prior run so
    that a gene is only accepted when it actually appeared in the results.
    """
    q = (query or "").upper()
    tokens = {token.strip(".,;:()[]{}") for token in re.split(r"\s+", q) if token}
    event_types = sorted({et for et in KNOWN_EVENT_TYPES if et in tokens})

    genes: list[str] = []
    for gene in known_genes or []:
        if not gene:
            continue
        if gene.upper() in tokens:
            genes.append(gene)
    genes = sorted(set(genes))

    return {"event_types": event_types, "genes": genes}


def build_followup_actions(
    intent: dict[str, Any], top_n: int | None = None
) -> list[tuple[str, dict[str, Any]]]:
    """Translate a parsed intent into a short action prefix.

    * a gene focus produces a single ``deep_dive_gene`` step;
    * an event-type restriction re-filters, re-ranks, re-interprets and
      re-reports with the narrowed event set.
    """
    actions: list[tuple[str, dict[str, Any]]] = []
    genes = intent.get("genes") or []
    event_types = intent.get("event_types") or []

    if genes:
        for gene in genes:
            actions.append(("deep_dive_gene", {"gene": gene}))
        actions.append(("generate_report", {}))
    elif event_types:
        actions.append(("filter_significant_events", {"event_types": list(event_types)}))
        actions.append(("rank_candidates", {"top_n": top_n}))
        actions.append(("interpret_candidates", {}))
        actions.append(("generate_report", {}))
    return actions
