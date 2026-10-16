"""Significance filtering and quality gating for AS events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from splicegaip.splicing.schema import StandardEvent


@dataclass(frozen=True)
class FilterSettings:
    """Significance gates and quality controls."""

    fdr_threshold: float = 0.05
    delta_psi_threshold: float = 0.1
    min_support_reads: int = 10
    min_valid_samples: int = 2


@dataclass(frozen=True)
class FilterReport:
    """What the filter did, for the methods section and workflow log."""

    input_count: int
    output_count: int
    fdr_threshold: float
    delta_psi_threshold: float
    min_support_reads: int
    min_valid_samples: int
    excluded: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "fdr_threshold": self.fdr_threshold,
            "delta_psi_threshold": self.delta_psi_threshold,
            "min_support_reads": self.min_support_reads,
            "min_valid_samples": self.min_valid_samples,
            "excluded": dict(self.excluded),
        }


def passes_significance(event: StandardEvent, settings: FilterSettings) -> bool:
    """FDR and effect-size gate."""
    if event.fdr is None or event.delta_psi is None:
        return False
    return event.fdr < settings.fdr_threshold and abs(event.delta_psi) > settings.delta_psi_threshold


def passes_quality(event: StandardEvent, settings: FilterSettings) -> tuple[bool, str]:
    """Quality gate; returns (passed, reason-if-failed)."""
    if event.single_sample_driven:
        return False, "single_sample_driven"
    if event.mapping_ambiguity:
        return False, "mapping_ambiguity"
    if event.total_support_reads is not None and event.total_support_reads < settings.min_support_reads:
        return False, "low_support_reads"
    if (
        event.valid_sample_count is not None
        and event.valid_sample_count < settings.min_valid_samples
    ):
        return False, "insufficient_valid_samples"
    return True, ""


def filter_significant_events(
    events: Sequence[StandardEvent],
    settings: FilterSettings | None = None,
) -> tuple[list[StandardEvent], FilterReport]:
    """Apply significance + quality gates, returning events and a report."""
    settings = settings or FilterSettings()
    kept: list[StandardEvent] = []
    excluded: dict[str, int] = {}
    for event in events:
        if not passes_significance(event, settings):
            excluded["not_significant"] = excluded.get("not_significant", 0) + 1
            continue
        passed, reason = passes_quality(event, settings)
        if not passed:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        kept.append(event)
    report = FilterReport(
        input_count=len(events),
        output_count=len(kept),
        fdr_threshold=settings.fdr_threshold,
        delta_psi_threshold=settings.delta_psi_threshold,
        min_support_reads=settings.min_support_reads,
        min_valid_samples=settings.min_valid_samples,
        excluded=excluded,
    )
    return kept, report
