"""SUPPA2 output parser.

SUPPA emits per-event-type ``.psi.tsv`` (per-sample PSI) and ``.dpsi``
(delta PSI) files. This parser merges them into standardized events:

* event id      -> SUPPA event id (``SE:chr:start-end:strand@gene``)
* event type    -> mapped from the SUPPA file prefix (SE/A3/A5/MX/RI/AF/AL)
* delta PSI     -> from the ``.dpsi`` column matching the two groups
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping

from splicegaip.splicing.schema import StandardEvent, _to_float

#: SUPPA event-type prefixes to the SpliceGAIP event-type vocabulary.
SUPPA_EVENT_TYPE_MAP: dict[str, str] = {
    "SE": "SE",
    "A3": "A3SS",
    "A5": "A5SS",
    "MX": "MXE",
    "RI": "RI",
    "AF": "AF",
    "AL": "AL",
}

#: SUPPA file suffixes, in parse priority order.
SUPPA_SUFFIXES: tuple[str, ...] = ("SE", "A3", "A5", "MX", "RI", "AF", "AL")


def _suppa_event_type(prefix: str) -> str:
    return SUPPA_EVENT_TYPE_MAP.get(prefix.upper(), prefix.upper())


def _event_parts(event_id: str) -> tuple[str, str, str]:
    """Split a SUPPA event id into (event_type, coordinates, gene_id).

    SUPPA event ids look like ``SE:chr17:7668402-7669538:+@ENSG00000141510``
    (the gene follows ``@``); some exports use ``;`` to join multiple
    alternative events.
    """
    coordinates, _, gene = event_id.partition("@")
    first = coordinates.split(";", 1)[0]
    event_type = first.split(":", 1)[0] if ":" in first else ""
    return event_type, first, gene


def parse_suppa_psi_file(
    path: str | Path,
    dpsi_values: Mapping[str, Mapping[str, float]] | None = None,
    group1_samples: list[str] | None = None,
    group2_samples: list[str] | None = None,
    fdr_values: Mapping[str, float] | None = None,
) -> list[StandardEvent]:
    """Parse one SUPPA ``.psi.tsv`` file into standardized events.

    :param path: the per-sample PSI file (e.g. ``SRR1_SE.psi.tsv``).
    :param dpsi_values: optional mapping event_id -> {group_pair: delta_psi}.
    :param group1_samples: control sample ids (for mean PSI).
    :param group2_samples: experimental sample ids (for mean PSI).
    :param fdr_values: optional mapping event_id -> FDR.
    """
    path = Path(path)
    if not path.is_file():
        return []
    group1_samples = group1_samples or []
    group2_samples = group2_samples or []
    events: list[StandardEvent] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        psi_columns = [name for name in (reader.fieldnames or []) if name not in {"gene_id"}]
        for raw in reader:
            event_id = str(raw.get("gene_id", "")).strip()
            parsed_type, coordinates, gene_symbol = _event_parts(event_id)
            psi_by_sample = {
                column: value
                for column in psi_columns
                for value in [_to_float(raw.get(column))]
                if value is not None
            }
            group1_psi = [psi_by_sample[sample] for sample in group1_samples if sample in psi_by_sample]
            group2_psi = [psi_by_sample[sample] for sample in group2_samples if sample in psi_by_sample]
            mean1 = sum(group1_psi) / len(group1_psi) if group1_psi else None
            mean2 = sum(group2_psi) / len(group2_psi) if group2_psi else None
            delta = None
            if dpsi_values and event_id in dpsi_values:
                pairs = dpsi_values[event_id]
                delta = next(iter(pairs.values()), None) if pairs else None
            if delta is None and mean1 is not None and mean2 is not None:
                delta = round(mean2 - mean1, 6)
            events.append(
                StandardEvent(
                    event_id=event_id,
                    gene_id=gene_symbol or event_id,
                    gene_symbol=gene_symbol,
                    event_type=_suppa_event_type(parsed_type),
                    chromosome=coordinates.split(":", 1)[1].split(":", 1)[0] if ":" in coordinates else "",
                    strand="",
                    genomic_coordinates=coordinates,
                    coordinate_system="suppa",
                    source_tool="SUPPA2",
                    mean_psi_group1=mean1,
                    mean_psi_group2=mean2,
                    delta_psi=delta,
                    p_value=None,
                    fdr=(fdr_values or {}).get(event_id),
                    psi_by_sample=psi_by_sample,
                    valid_sample_count=len(psi_by_sample),
                )
            )
    return events


def is_suppa_directory(path: str | Path) -> bool:
    """Heuristic: directory containing ``*_SE.psi.tsv`` style files."""
    directory = Path(path)
    if not directory.is_dir():
        return False
    return any(next(directory.glob(f"*_{suffix}.psi.tsv"), None) is not None for suffix in SUPPA_SUFFIXES)
