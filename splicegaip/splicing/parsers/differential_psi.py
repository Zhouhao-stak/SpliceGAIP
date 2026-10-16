"""Parser for the common "differential splicing results + PSI matrix + sample
metadata" CSV trio.

Many pipelines (and plain spreadsheet exports) emit three sidecar files instead
of a single rMATS / SUPPA2 dump:

* ``differential_splicing_results.csv`` -- one row per ``(gene, event_type)``
  carrying the effect size (``ΔPSI`` / ``dPSI`` / ``delta_psi``), an FDR and a
  p-value. Column names vary between tools and locales, so matching is
  case-insensitive and accepts a few common aliases.
* ``psi_matrix.csv`` -- one row per gene with a per-sample PSI column.
* ``sample_metadata.csv`` -- sample id plus a grouping column (``Condition`` /
  ``group`` / ...).

This normalizes them into the ``AS_event_master`` contract so the rest of the
platform can consume them exactly like any rMATS or SUPPA2 input. Genomic
coordinates are usually absent from this format; they are left empty and noted
in the report's limitations section rather than blocking the analysis.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping

from splicegaip.splicing.schema import StandardEvent, _to_float

#: Candidate file names for the differential-results table.
DIFF_FILENAMES = (
    "differential_splicing_results.csv",
    "differential_splicing_results.tsv",
    "diff_splicing_results.csv",
    "splicing_results.csv",
    "differential_splicing.tsv",
)
#: Candidate file names for the per-sample PSI matrix.
PSI_FILENAMES = (
    "psi_matrix.csv",
    "psi_matrix.tsv",
    "psi_table.csv",
    "PSI_matrix.csv",
    "psi_by_sample.csv",
)


def _normalize(name: str) -> str:
    return name.strip().lower()


def _find_col(header: list[str], *candidates: str) -> str | None:
    """Return the original header name whose normalized form matches a candidate.

    Matching is case-insensitive and ignores surrounding whitespace so that
    ``Gene``, ``gene`` and ``GENE`` all resolve to the same column.
    """
    lookup = {_normalize(h): h for h in header if h}
    for candidate in candidates:
        key = _normalize(candidate)
        if key in lookup:
            return lookup[key]
    return None


def _delimiter(path: Path) -> str:
    return "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=_delimiter(path))
        header = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return header, rows


def is_differential_psi_directory(directory: str | Path) -> bool:
    """Heuristic: a directory holding both a differential-results table and a
    per-sample PSI matrix."""
    directory = Path(directory)
    if not directory.is_dir():
        return False
    diff = next((directory / name for name in DIFF_FILENAMES if (directory / name).is_file()), None)
    psi = next((directory / name for name in PSI_FILENAMES if (directory / name).is_file()), None)
    return diff is not None and psi is not None


def parse_differential_psi_directory(
    directory: str | Path,
    group1_samples: list[str] | None = None,
    group2_samples: list[str] | None = None,
) -> list[StandardEvent]:
    """Parse a differential-results + PSI-matrix directory into standardized events."""
    directory = Path(directory)
    diff_path = next((directory / name for name in DIFF_FILENAMES if (directory / name).is_file()), None)
    psi_path = next((directory / name for name in PSI_FILENAMES if (directory / name).is_file()), None)
    if not diff_path or not psi_path:
        return []

    # --- load the PSI matrix: gene symbol -> {sample_id: psi} ------------------
    _, psi_rows = _read_rows(psi_path)
    header = list(psi_rows[0].keys()) if psi_rows else []
    gene_col = _find_col(header, "Gene", "gene_symbol", "gene", "Gene_Symbol", "ID")
    psi_by_gene: dict[str, dict[str, float]] = {}
    if gene_col and psi_rows:
        sample_ids = [col for col in header if col != gene_col]
        for row in psi_rows:
            gene = str(row.get(gene_col, "")).strip()
            if not gene:
                continue
            psi_by_gene[gene] = {
                sid: value
                for sid in sample_ids
                if (value := _to_float(row.get(sid))) is not None
            }

    # --- load the differential results ---------------------------------------
    diff_header, diff_rows = _read_rows(diff_path)
    gene_c = _find_col(diff_header, "Gene", "gene_symbol", "gene", "Gene_Symbol")
    type_c = _find_col(diff_header, "Event_Type", "event_type", "EventType", "type")
    dpsi_c = _find_col(diff_header, "ΔPSI", "δPSI", "dPSI", "delta_psi", "deltaPSI", "dpsi", "PSI_delta")
    fdr_c = _find_col(diff_header, "FDR", "fdr", "q_value", "qvalue", "adj_pval")
    p_c = _find_col(diff_header, "P_Value", "p_value", "PValue", "pvalue", "p_val")
    if not gene_c or not type_c or not dpsi_c:
        return []

    group1 = group1_samples or []
    group2 = group2_samples or []

    def _group_mean(psi: Mapping[str, float], samples: list[str]) -> float | None:
        values = [psi[sid] for sid in samples if sid in psi]
        return sum(values) / len(values) if values else None

    events: list[StandardEvent] = []
    counters: dict[tuple[str, str], int] = {}
    for row in diff_rows:
        gene = str(row.get(gene_c, "")).strip()
        event_type = str(row.get(type_c, "")).strip().upper()
        if not gene or not event_type:
            continue
        counters[(gene, event_type)] = counters.get((gene, event_type), 0) + 1
        occurrence = counters[(gene, event_type)]
        psi = dict(psi_by_gene.get(gene, {}))
        events.append(
            StandardEvent(
                event_id=f"{gene}|{event_type}|{occurrence}",
                gene_id=gene,
                gene_symbol=gene,
                event_type=event_type,
                chromosome="",
                strand="",
                genomic_coordinates="",
                coordinate_system="unspecified",
                source_tool="differential_psi",
                mean_psi_group1=_group_mean(psi, group1),
                mean_psi_group2=_group_mean(psi, group2),
                delta_psi=_to_float(row.get(dpsi_c)),
                p_value=_to_float(row.get(p_c)) if p_c else None,
                fdr=_to_float(row.get(fdr_c)) if fdr_c else None,
                psi_by_sample=psi,
                valid_sample_count=len(psi),
            )
        )
    return events
