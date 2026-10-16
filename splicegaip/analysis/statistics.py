"""Statistical primitives for alternative-splicing analysis.

The chi-square test and Benjamini-Hochberg adjustment are ported from the
SplicingNexus v2 production implementation (``stage1_docker_adapter``).
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from splicegaip.splicing.schema import StandardEvent


def chi_square_p_value(
    control_in: float,
    control_out: float,
    experiment_in: float,
    experiment_out: float,
) -> float | None:
    """Two-by-two chi-square test p-value on junction counts.

    Equivalent to rMATS' JC-based test. Returns ``None`` when any marginal
    is zero (undefined test).
    """
    cells = (control_in, control_out, experiment_in, experiment_out)
    total = sum(cells)
    row_control = control_in + control_out
    row_experiment = experiment_in + experiment_out
    column_in = control_in + experiment_in
    column_out = control_out + experiment_out
    if min(total, row_control, row_experiment, column_in, column_out) <= 0:
        return None
    expected = (
        row_control * column_in / total,
        row_control * column_out / total,
        row_experiment * column_in / total,
        row_experiment * column_out / total,
    )
    if any(value <= 0 for value in expected):
        return None
    statistic = sum((observed - target) ** 2 / target for observed, target in zip(cells, expected))
    # Chi-square with 1 degree of freedom: p = erfc(sqrt(statistic / 2)).
    return math.erfc(math.sqrt(max(0.0, statistic) / 2.0))


def benjamini_hochberg(p_values: Sequence[float | None]) -> list[float | None]:
    """Benjamini-Hochberg FDR adjustment, preserving ``None`` entries."""
    indexed = [
        (index, float(value))
        for index, value in enumerate(p_values)
        if value is not None
    ]
    indexed.sort(key=lambda item: item[1])
    adjusted: dict[int, float] = {}
    running = 1.0
    total = len(indexed)
    for rank_index in range(total - 1, -1, -1):
        row_index, p_value = indexed[rank_index]
        running = min(running, p_value * total / (rank_index + 1))
        adjusted[row_index] = min(1.0, running)
    return [adjusted.get(index) for index in range(len(p_values))]


def recompute_fdr(events: Sequence[StandardEvent]) -> None:
    """Recompute FDR from p-values in place (BH adjustment)."""
    adjusted = benjamini_hochberg([event.p_value for event in events])
    for event, fdr in zip(events, adjusted):
        if event.fdr is None and fdr is not None:
            event.fdr = round(fdr, 12)


def effect_size_summary(events: Sequence[StandardEvent]) -> dict[str, Any]:
    """Summarize delta-PSI distribution of an event collection."""
    deltas = [event.delta_psi for event in events if event.delta_psi is not None]
    if not deltas:
        return {"count": 0, "mean_abs_delta_psi": None, "max_abs_delta_psi": None}
    absolute = [abs(value) for value in deltas]
    return {
        "count": len(deltas),
        "mean_abs_delta_psi": round(sum(absolute) / len(absolute), 6),
        "max_abs_delta_psi": round(max(absolute), 6),
    }
