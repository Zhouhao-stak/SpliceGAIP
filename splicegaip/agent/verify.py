"""Result verification: the agent's quality control.

After every observation the state is checked against a rule set. Each rule
emits an :class:`~splicegaip.agent.state.Issue` with a severity and, when the
agent can do something about it, a suggestion (which the reflector turns
into an action).
"""

from __future__ import annotations

from typing import Any

from .state import BLOCKER, INFO, WARNING, AgentState, Issue

#: More than this many significant events means the gate is too loose.
TOO_MANY_SIGNIFICANT = 2000
#: Fewer than this means the analysis will have nothing to say.
TOO_FEW_SIGNIFICANT = 5


def _rule_no_significant(state: AgentState) -> Issue | None:
    if not state.facts.get("filtered"):
        return None
    if int(state.facts.get("significant", 0)) > 0:
        return None
    return Issue(
        code="no_significant_events",
        severity=BLOCKER,
        message="Significance filtering produced zero events; downstream analysis would be empty.",
        suggestion="Relax the gates from the data (adapt_thresholds, strategy=exploratory) and re-filter.",
    )


def _rule_too_many_significant(state: AgentState) -> Issue | None:
    if not state.facts.get("filtered"):
        return None
    count = int(state.facts.get("significant", 0))
    if count <= TOO_MANY_SIGNIFICANT:
        return None
    return Issue(
        code="too_many_significant",
        severity=WARNING,
        message=f"{count} significant events: the gate is too loose to prioritize anything.",
        suggestion="Tighten the gates (adapt_thresholds, strategy=strict) and re-filter.",
    )


def _rule_few_significant(state: AgentState) -> Issue | None:
    if not state.facts.get("filtered"):
        return None
    count = int(state.facts.get("significant", 0))
    if count == 0 or count >= TOO_FEW_SIGNIFICANT:
        return None
    return Issue(
        code="few_significant_events",
        severity=WARNING,
        message=f"Only {count} significant events; conclusions will be fragile.",
        suggestion="Try a more exploratory gate before reporting.",
    )


def _rule_no_candidates(state: AgentState) -> Issue | None:
    if not state.facts.get("filtered") or int(state.facts.get("significant", 0)) == 0:
        return None
    # Only meaningful once ranking has actually been attempted.
    if not any(step.action == "rank_candidates" for step in state.steps):
        return None
    if int(state.facts.get("candidates", 0)) > 0:
        return None
    return Issue(
        code="no_candidates",
        severity=BLOCKER,
        message="Ranking produced no candidates although significant events exist.",
        suggestion="Re-run ranking (or relax the gates) before interpreting.",
    )


def _rule_missing_fdr(state: AgentState) -> Issue | None:
    profile = state.profile or {}
    coverage = profile.get("fdr_coverage")
    if coverage is None or coverage >= 0.5:
        return None
    return Issue(
        code="sparse_fdr_coverage",
        severity=WARNING,
        message=f"Only {coverage:.0%} of events carry an FDR value; significance is partly unavailable.",
        suggestion="Report the limitation explicitly; the filter recomputes FDR from p-values where possible.",
    )


def _rule_small_dataset(state: AgentState) -> Issue | None:
    if int(state.facts.get("events_total", 0)) >= 50:
        return None
    return Issue(
        code="small_dataset",
        severity=INFO,
        message=f"Only {state.facts.get('events_total')} events: treat every conclusion as exploratory.",
        suggestion="State the sample-size limitation in the report.",
    )


def _rule_imbalanced_groups(state: AgentState) -> Issue | None:
    imbalance = (state.profile or {}).get("group_imbalance")
    if not imbalance or imbalance < 3:
        return None
    return Issue(
        code="imbalanced_groups",
        severity=INFO,
        message=f"Group sizes differ by {imbalance}x; group comparisons are unbalanced.",
        suggestion="Mention the imbalance in the limitations section.",
    )


def _rule_enrichment_unavailable(state: AgentState) -> Issue | None:
    if not state.facts.get("filtered") or state.facts.get("has_annotation"):
        return None
    return Issue(
        code="enrichment_unavailable",
        severity=INFO,
        message="No gene annotation table supplied; functional enrichment cannot run.",
        suggestion="Report enrichment as unavailable rather than substituting speculation.",
    )


def _rule_sparse_evidence(state: AgentState) -> Issue | None:
    targets = int(state.facts.get("evidence_targets", 0))
    covered = int(state.facts.get("evidence_genes", 0))
    if targets == 0 or covered / max(targets, 1) >= 0.3:
        return None
    return Issue(
        code="sparse_evidence",
        severity=WARNING,
        message=f"Literature evidence covers only {covered}/{targets} candidate genes.",
        suggestion="Retry evidence collection with a higher per-gene limit.",
    )


def _rule_figures_missing(state: AgentState) -> Issue | None:
    if not any(step.action == "generate_figures" for step in state.steps):
        return None
    if int(state.facts.get("figures", 0)) > 0:
        return None
    return Issue(
        code="figures_missing",
        severity=WARNING,
        message="Figure generation ran but produced no figures.",
        suggestion="Retry figure generation once.",
    )


def _rule_confounded(state: AgentState) -> Issue | None:
    """A rejected hypothesis test means the result needs a caveat."""
    confounds = state.facts.get("hypothesis_confounds") or []
    if not confounds:
        return None
    labels = ", ".join(str(item) for item in confounds)
    return Issue(
        code="result_confounded",
        severity=WARNING,
        message=f"Hypothesis tests flagged a confound ({labels}); conclusions need a caveat.",
        suggestion="State the confound in the limitations and avoid causal wording for these events.",
    )


def _rule_repeated_failures(state: AgentState) -> Issue | None:
    failures = [step for step in state.steps if step.status == "error"]
    if len(failures) < 2:
        return None
    return Issue(
        code="repeated_failures",
        severity=WARNING,
        message=f"{len(failures)} actions failed: {', '.join(sorted({step.action for step in failures}))}.",
        suggestion="Continue with what succeeded and record the failures in the limitations.",
    )


RULES = (
    _rule_no_significant,
    _rule_no_candidates,
    _rule_too_many_significant,
    _rule_few_significant,
    _rule_missing_fdr,
    _rule_sparse_evidence,
    _rule_figures_missing,
    _rule_confounded,
    _rule_repeated_failures,
    _rule_enrichment_unavailable,
    _rule_small_dataset,
    _rule_imbalanced_groups,
)


def verify_state(state: AgentState) -> list[Issue]:
    """Run every rule and return the issues found (replacing the old set)."""
    issues: list[Issue] = []
    for rule in RULES:
        try:
            issue = rule(state)
        except Exception:  # noqa: BLE001 - a broken rule must not stall the run
            continue
        if issue is not None:
            issues.append(issue)
    accepted = {
        item.get("code")
        for item in state.facts.get("accepted_limitations", [])
        if isinstance(item, dict)
    }
    if accepted:
        downgraded: list[Issue] = []
        for issue in issues:
            if issue.code in accepted:
                downgraded.append(
                    Issue(issue.code, INFO, issue.message, "Accepted limitation (no further remediation).")
                )
            else:
                downgraded.append(issue)
        issues = downgraded
    state.issues = issues
    return issues


def issue_summary(issues: list[Issue]) -> dict[str, Any]:
    """Counts by severity, for logs and the API payload."""
    return {
        "total": len(issues),
        "blocker": sum(1 for item in issues if item.severity == BLOCKER),
        "warning": sum(1 for item in issues if item.severity == WARNING),
        "info": sum(1 for item in issues if item.severity == INFO),
    }
