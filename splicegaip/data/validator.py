"""Dataset validation.

Validation is advisory-by-default: structural problems are *errors* (the
dataset cannot be analyzed), while data-quality problems are *warnings*
(the analysis proceeds and the warnings are carried into the report's
limitations section).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from splicegaip.data.loader import Dataset
from splicegaip.splicing.schema import AS_EVENT_TYPES

MAX_PSI = 1.0
MIN_PSI = 0.0


@dataclass(frozen=True)
class ValidationIssue:
    """One validation finding."""

    severity: str  # "error" or "warning"
    code: str
    message: str


@dataclass
class ValidationResult:
    """Aggregated validation result for a dataset."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [
                {"severity": issue.severity, "code": issue.code, "message": issue.message}
                for issue in self.issues
            ],
        }


def validate_dataset(dataset: Dataset) -> ValidationResult:
    """Validate a loaded dataset against the Standard BioAnalysis Format."""
    result = ValidationResult()

    if not dataset.events:
        result.issues.append(
            ValidationIssue("error", "no_events", "Dataset contains no AS events.")
        )
        return result

    # --- structural checks -------------------------------------------------
    missing_id = sum(1 for event in dataset.events if not event.event_id)
    if missing_id:
        result.issues.append(
            ValidationIssue("error", "missing_event_id", f"{missing_id} events lack an event_id.")
        )
    duplicate_ids = len(dataset.events) - len({event.event_id for event in dataset.events})
    if duplicate_ids:
        result.issues.append(
            ValidationIssue("warning", "duplicate_event_id", f"{duplicate_ids} duplicate event_id values found.")
        )
    missing_gene = sum(1 for event in dataset.events if not (event.gene_id or event.gene_symbol))
    if missing_gene:
        result.issues.append(
            ValidationIssue("error", "missing_gene", f"{missing_gene} events lack a gene identifier.")
        )
    unknown_types = sorted(
        {event.event_type for event in dataset.events if event.event_type not in AS_EVENT_TYPES}
    )
    if unknown_types:
        result.issues.append(
            ValidationIssue(
                "warning",
                "unknown_event_type",
                f"Event types outside {list(AS_EVENT_TYPES)}: {unknown_types}.",
            )
        )

    # --- statistical checks ------------------------------------------------
    no_fdr = sum(1 for event in dataset.events if event.fdr is None)
    if no_fdr == len(dataset.events):
        result.issues.append(
            ValidationIssue(
                "warning",
                "no_fdr",
                "No FDR values present; significance filtering will select nothing. "
                "Provide an FDR column or let the analyst recompute it from p-values.",
            )
        )
    elif no_fdr:
        result.issues.append(
            ValidationIssue("warning", "partial_fdr", f"{no_fdr} events lack FDR values.")
        )
    no_delta = sum(1 for event in dataset.events if event.delta_psi is None)
    if no_delta:
        result.issues.append(
            ValidationIssue("warning", "missing_delta_psi", f"{no_delta} events lack delta_PSI values.")
        )
    out_of_range = sum(
        1
        for event in dataset.events
        for value in (event.mean_psi_group1, event.mean_psi_group2)
        if value is not None and not (MIN_PSI <= value <= MAX_PSI)
    )
    if out_of_range:
        result.issues.append(
            ValidationIssue(
                "warning", "psi_out_of_range", f"{out_of_range} group PSI values outside [0, 1]."
            )
        )

    # --- sample / group checks ---------------------------------------------
    groups = dataset.groups
    if dataset.samples and len(groups) < 2:
        result.issues.append(
            ValidationIssue(
                "error",
                "single_group",
                "Sample metadata defines fewer than two groups; differential analysis "
                "requires a control and an experimental group.",
            )
        )
    psi_samples = {
        sample_id for event in dataset.events for sample_id in event.psi_by_sample
    }
    metadata_samples = {sample.sample_id for sample in dataset.samples}
    if psi_samples and metadata_samples and not psi_samples & metadata_samples:
        result.issues.append(
            ValidationIssue(
                "warning",
                "psi_sample_mismatch",
                "Per-sample PSI columns do not overlap with sample_metadata sample ids.",
            )
        )

    return result
