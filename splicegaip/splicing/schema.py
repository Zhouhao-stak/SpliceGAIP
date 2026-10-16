"""Standard AS event schema (``AS_event_master`` contract).

Ported from the SplicingNexus v2 event contract. The core columns are the
ones required by the SpliceGAIP prompt; the quality columns follow the
SplicingNexus production contract and are optional on input.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

AS_EVENT_TYPES: tuple[str, ...] = ("SE", "MXE", "A5SS", "A3SS", "RI")

#: Columns that must be present in any standardized event table.
CORE_EVENT_FIELDS: tuple[str, ...] = (
    "event_id",
    "gene_id",
    "gene_symbol",
    "event_type",
    "chromosome",
    "strand",
    "genomic_coordinates",
    "coordinate_system",
    "source_tool",
    "mean_PSI_group1",
    "mean_PSI_group2",
    "delta_PSI",
    "p_value",
    "FDR",
)

#: Optional quality / confidence columns (SplicingNexus contract).
QUALITY_EVENT_FIELDS: tuple[str, ...] = (
    "inclusion_reads",
    "exclusion_reads",
    "total_support_reads",
    "valid_sample_count",
    "psi_missing_rate",
    "single_sample_driven",
    "mapping_ambiguity",
    "confidence_level",
    "ranking_basis",
)

AS_EVENT_FIELDS: tuple[str, ...] = CORE_EVENT_FIELDS + QUALITY_EVENT_FIELDS

#: Sample-level PSI columns use the ``PSI_<sample_id>`` prefix.
PSI_COLUMN_PREFIX = "PSI_"

NUMERIC_EVENT_FIELDS: tuple[str, ...] = (
    "mean_PSI_group1",
    "mean_PSI_group2",
    "delta_PSI",
    "p_value",
    "FDR",
    "inclusion_reads",
    "exclusion_reads",
    "total_support_reads",
    "valid_sample_count",
    "psi_missing_rate",
)


@dataclass(frozen=True)
class SampleMetadata:
    """One sample row from ``sample_metadata.tsv``."""

    sample_id: str
    group: str
    condition: str = ""
    tissue: str = ""
    batch: str = ""
    extra: Mapping[str, str] = field(default_factory=dict)


@dataclass
class StandardEvent:
    """One standardized alternative-splicing event."""

    event_id: str
    gene_id: str
    gene_symbol: str
    event_type: str
    chromosome: str
    strand: str
    genomic_coordinates: str
    coordinate_system: str
    source_tool: str
    mean_psi_group1: float | None
    mean_psi_group2: float | None
    delta_psi: float | None
    p_value: float | None
    fdr: float | None
    psi_by_sample: dict[str, float] = field(default_factory=dict)
    inclusion_reads: int | None = None
    exclusion_reads: int | None = None
    total_support_reads: int | None = None
    valid_sample_count: int | None = None
    single_sample_driven: bool | None = None
    mapping_ambiguity: bool | None = None
    confidence_level: str = ""

    def to_row(self, sample_ids: Iterable[str] = ()) -> dict[str, Any]:
        row: dict[str, Any] = {
            "event_id": self.event_id,
            "gene_id": self.gene_id,
            "gene_symbol": self.gene_symbol,
            "event_type": self.event_type,
            "chromosome": self.chromosome,
            "strand": self.strand,
            "genomic_coordinates": self.genomic_coordinates,
            "coordinate_system": self.coordinate_system,
            "source_tool": self.source_tool,
            "mean_PSI_group1": self.mean_psi_group1,
            "mean_PSI_group2": self.mean_psi_group2,
            "delta_PSI": self.delta_psi,
            "p_value": self.p_value,
            "FDR": self.fdr,
            "inclusion_reads": self.inclusion_reads,
            "exclusion_reads": self.exclusion_reads,
            "total_support_reads": self.total_support_reads,
        }
        for sample_id in sample_ids:
            row[f"{PSI_COLUMN_PREFIX}{sample_id}"] = self.psi_by_sample.get(sample_id, "")
        return row


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "NA", "NaN", "nan", "None"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    number = _to_float(value)
    return None if number is None else int(round(number))


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def parse_event_row(raw: Mapping[str, Any]) -> StandardEvent:
    """Parse one raw TSV/CSV row into a :class:`StandardEvent`."""
    psi_by_sample = {
        key[len(PSI_COLUMN_PREFIX):]: value
        for key, value in raw.items()
        if key.startswith(PSI_COLUMN_PREFIX)
        for value in [_to_float(value)]
        if value is not None
    }
    return StandardEvent(
        event_id=str(raw.get("event_id", "")).strip(),
        gene_id=str(raw.get("gene_id", "")).strip(),
        gene_symbol=str(raw.get("gene_symbol", "")).strip(),
        event_type=str(raw.get("event_type", "")).strip().upper(),
        chromosome=str(raw.get("chromosome", "")).strip(),
        strand=str(raw.get("strand", "")).strip(),
        genomic_coordinates=str(raw.get("genomic_coordinates", "")).strip(),
        coordinate_system=str(raw.get("coordinate_system", "")).strip(),
        source_tool=str(raw.get("source_tool", "")).strip(),
        mean_psi_group1=_to_float(raw.get("mean_PSI_group1")),
        mean_psi_group2=_to_float(raw.get("mean_PSI_group2")),
        delta_psi=_to_float(raw.get("delta_PSI")),
        p_value=_to_float(raw.get("p_value")),
        fdr=_to_float(raw.get("FDR")),
        psi_by_sample=psi_by_sample,
        inclusion_reads=_to_int(raw.get("inclusion_reads")),
        exclusion_reads=_to_int(raw.get("exclusion_reads")),
        total_support_reads=_to_int(raw.get("total_support_reads")),
        valid_sample_count=_to_int(raw.get("valid_sample_count")),
        single_sample_driven=_to_bool(raw.get("single_sample_driven")),
        mapping_ambiguity=_to_bool(raw.get("mapping_ambiguity")),
        confidence_level=str(raw.get("confidence_level", "")).strip(),
    )


def load_events_tsv(path: str | Path) -> list[StandardEvent]:
    """Load a standardized event table (TSV or CSV) from ``path``."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Event table not found: {path}")
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [parse_event_row(raw) for raw in reader]


def load_sample_metadata(path: str | Path) -> list[SampleMetadata]:
    """Load ``sample_metadata.tsv`` / ``.csv`` describing samples and groups.

    Accepts both tab- and comma-separated inputs. The grouping column is read
    from ``group`` first and falls back to ``Condition`` / ``condition`` (a very
    common alternative header in spreadsheet exports).
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Sample metadata not found: {path}")
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    samples: list[SampleMetadata] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter=delimiter):
            sample_id = str(raw.get("sample_id") or raw.get("Sample_ID") or "").strip()
            if not sample_id:
                continue
            group = str(
                raw.get("group") or raw.get("Condition") or raw.get("condition") or ""
            ).strip()
            condition = str(raw.get("condition") or raw.get("Condition") or "").strip()
            tissue = str(raw.get("tissue") or raw.get("Tissue") or "").strip()
            batch = str(raw.get("batch") or raw.get("Batch") or "").strip()
            samples.append(
                SampleMetadata(
                    sample_id=sample_id,
                    group=group,
                    condition=condition,
                    tissue=tissue,
                    batch=batch,
                    extra={
                        key: value
                        for key, value in raw.items()
                        if key
                        not in {
                            "sample_id",
                            "Sample_ID",
                            "group",
                            "condition",
                            "Condition",
                            "tissue",
                            "Tissue",
                            "batch",
                            "Batch",
                        }
                    },
                )
            )
    return samples


def group_sample_ids(samples: Iterable[SampleMetadata]) -> dict[str, list[str]]:
    """Group sample ids by their ``group`` label."""
    groups: dict[str, list[str]] = {}
    for sample in samples:
        groups.setdefault(sample.group, []).append(sample.sample_id)
    return groups
