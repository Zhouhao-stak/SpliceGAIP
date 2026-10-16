"""Dataset profiling: what the agent must know before it can decide.

The profile is the agent's senses. It answers, in numbers:

* how much data is there, and of which event types;
* how complete is it (FDR / delta-PSI / PSI coverage, support reads);
* how balanced are the groups;
* what looks suspicious (flags).
"""

from __future__ import annotations

from typing import Any

from splicegaip.tools.context import RunContext


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _ratio(events: list[Any], attribute: str) -> float:
    if not events:
        return 0.0
    hits = sum(1 for event in events if getattr(event, attribute, None) is not None)
    return round(hits / len(events), 4)


def build_profile(context: RunContext) -> dict[str, Any]:
    """Compute the dataset profile (pure read, no side effects)."""
    dataset = context.dataset
    events = dataset.events
    groups = dataset.groups

    event_types: dict[str, int] = {}
    for event in events:
        event_types[event.event_type] = event_types.get(event.event_type, 0) + 1

    support = [
        event.total_support_reads
        for event in events
        if event.total_support_reads is not None
    ]
    psi_missing = [
        value
        for value in (getattr(event, "psi_missing_rate", None) for event in events)
        if value is not None
    ]
    group_sizes = {name: len(ids) for name, ids in groups.items()}
    sizes = sorted(group_sizes.values())
    imbalance = round(sizes[-1] / sizes[0], 2) if len(sizes) >= 2 and sizes[0] else None

    flags: list[str] = []
    fdr_coverage = _ratio(events, "fdr")
    delta_coverage = _ratio(events, "delta_psi")
    median_support = _median([float(value) for value in support])

    if len(events) < 50:
        flags.append("small_dataset")
    if fdr_coverage < 0.5:
        flags.append("sparse_fdr")
    if delta_coverage < 0.5:
        flags.append("sparse_delta_psi")
    if median_support is not None and median_support < 20:
        flags.append("low_support_reads")
    if imbalance is not None and imbalance >= 3:
        flags.append("imbalanced_groups")
    if not dataset.samples:
        flags.append("no_sample_metadata")
    if not dataset.annotation:
        flags.append("no_annotation")
    if psi_missing and _median(psi_missing) > 0.3:  # type: ignore[arg-type]
        flags.append("high_psi_missing_rate")

    return {
        "event_count": len(events),
        "sample_count": len(dataset.samples),
        "source_format": dataset.source_format,
        "event_types": event_types,
        "groups": group_sizes,
        "group_imbalance": imbalance,
        "fdr_coverage": fdr_coverage,
        "delta_psi_coverage": delta_coverage,
        "p_value_coverage": _ratio(events, "p_value"),
        "median_support_reads": median_support,
        "min_support_reads": min(support) if support else None,
        "median_psi_missing_rate": _median(psi_missing),
        "annotated_genes": len(dataset.annotation),
        "de_gene_count": len(dataset.de_genes),
        "flags": flags,
    }


def profile_text(profile: dict[str, Any]) -> str:
    """Human-readable one-paragraph rendering of the profile."""
    types = ", ".join(f"{key}={value}" for key, value in sorted(profile["event_types"].items()))
    groups = ", ".join(f"{key}={value}" for key, value in sorted(profile["groups"].items()))
    flags = ", ".join(profile["flags"]) or "none"
    return (
        f"Profile: {profile['event_count']} events ({types}); "
        f"{profile['sample_count']} samples ({groups or 'unspecified'}); "
        f"FDR coverage={profile['fdr_coverage']}, dPSI coverage={profile['delta_psi_coverage']}, "
        f"median support reads={profile['median_support_reads']}; "
        f"annotation={profile['annotated_genes']} genes, DE rows={profile['de_gene_count']}; "
        f"flags: {flags}"
    )
