"""Data layer package: loading and validation of analysis inputs."""

from splicegaip.data.loader import (
    DE_FIELDS,
    Dataset,
    DifferentialGene,
    load_dataset,
    load_differential_expression,
)
from splicegaip.data.validator import ValidationIssue, ValidationResult, validate_dataset

__all__ = [
    "DE_FIELDS",
    "Dataset",
    "DifferentialGene",
    "ValidationIssue",
    "ValidationResult",
    "load_dataset",
    "load_differential_expression",
    "validate_dataset",
]
