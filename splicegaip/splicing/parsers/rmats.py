"""rMATS output parser.

Ported and generalized from the SplicingNexus v2 production normalizer
(``stage1_docker_adapter.normalise_rmats_results``): converts rMATS
junction-count (JC) tables for SE / A5SS / A3SS / MXE / RI events into the
standardized ``AS_event_master`` contract.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping

from splicegaip.splicing.schema import StandardEvent, _to_float, _to_int

#: rMATS JC output file name for each supported event type.
RMATS_EVENT_FILES: dict[str, str] = {
    "SE": "SE.MATS.JC.txt",
    "A5SS": "A5SS.MATS.JC.txt",
    "A3SS": "A3SS.MATS.JC.txt",
    "MXE": "MXE.MATS.JC.txt",
    "RI": "RI.MATS.JC.txt",
}

#: rMATS coordinate fields used to build the genomic coordinate string.
_RMATS_COORDINATE_FIELDS: dict[str, tuple[str, str]] = {
    "SE": ("exonStart_0base", "exonEnd"),
    "RI": ("upstreamEE", "downstreamES"),
    "A5SS": ("longExonStart_0base", "longExonEnd"),
    "A3SS": ("longExonStart_0base", "longExonEnd"),
    "MXE": ("1stExonStart_0base", "2ndExonEnd"),
}


def _numbers(value: Any, cast: type[float] | type[int]) -> list[float] | list[int]:
    values: list[float] | list[int] = []
    for item in str(value or "").split(","):
        if item.strip() in {"", "NA", "nan", "NaN"}:
            continue
        try:
            values.append(cast(item.strip()))
        except ValueError:
            continue
    return values


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _coordinates(event_type: str, row: Mapping[str, str]) -> str:
    """Build ``chr:start-end`` with 1-based inclusive coordinates.

    rMATS start fields are zero-based; the platform contract uses 1-based
    inclusive coordinates like GTF/GFF.
    """
    start_field, end_field = _RMATS_COORDINATE_FIELDS[event_type]
    raw_start = row.get(start_field, "")
    try:
        start = str(int(raw_start) + 1)
    except (TypeError, ValueError):
        start = raw_start
    return f"{row.get('chr', '')}:{start}-{row.get(end_field, '')}"


def parse_rmats_file(
    path: str | Path,
    event_type: str,
    group1_samples: list[str],
    group2_samples: list[str],
) -> list[StandardEvent]:
    """Parse one rMATS JC table into standardized events.

    :param path: rMATS output file (e.g. ``SE.MATS.JC.txt``).
    :param event_type: one of SE / A5SS / A3SS / MXE / RI.
    :param group1_samples: sample ids of the control group (rMATS sample set 1).
    :param group2_samples: sample ids of the experimental group (rMATS sample set 2).
    """
    path = Path(path)
    if not path.is_file():
        return []
    sample_ids = [*group1_samples, *group2_samples]
    events: list[StandardEvent] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter="\t"):
            control_psi = _numbers(raw.get("IncLevel1"), float)
            experiment_psi = _numbers(raw.get("IncLevel2"), float)
            mean_control, mean_experiment = _mean(control_psi), _mean(experiment_psi)
            inclusion = sum(_numbers(raw.get("IJC_SAMPLE_1"), int)) + sum(
                _numbers(raw.get("IJC_SAMPLE_2"), int)
            )
            exclusion = sum(_numbers(raw.get("SJC_SAMPLE_1"), int)) + sum(
                _numbers(raw.get("SJC_SAMPLE_2"), int)
            )
            psi_values = [*control_psi, *experiment_psi]
            psi_by_sample = {
                sample_id: psi_values[index]
                for index, sample_id in enumerate(sample_ids)
                if index < len(psi_values)
            }
            delta = (
                None
                if mean_control is None or mean_experiment is None
                else round(mean_experiment - mean_control, 6)
            )
            events.append(
                StandardEvent(
                    event_id=f"{event_type}:{raw.get('ID', len(events) + 1)}",
                    gene_id=str(raw.get("GeneID", "")).strip('"'),
                    gene_symbol=str(raw.get("geneSymbol", "")).strip('"'),
                    event_type=event_type,
                    chromosome=str(raw.get("chr", "")).strip(),
                    strand=str(raw.get("strand", "")).strip(),
                    genomic_coordinates=_coordinates(event_type, raw),
                    coordinate_system="1-based-inclusive",
                    source_tool="rMATS",
                    mean_psi_group1=mean_control,
                    mean_psi_group2=mean_experiment,
                    delta_psi=delta,
                    p_value=_to_float(raw.get("PValue")),
                    fdr=_to_float(raw.get("FDR")),
                    psi_by_sample=psi_by_sample,
                    inclusion_reads=inclusion,
                    exclusion_reads=exclusion,
                    total_support_reads=inclusion + exclusion,
                    valid_sample_count=len(psi_by_sample),
                )
            )
    return events


def parse_rmats_directory(
    rmats_output: str | Path,
    group1_samples: list[str],
    group2_samples: list[str],
) -> list[StandardEvent]:
    """Parse all rMATS JC tables found in ``rmats_output``."""
    directory = Path(rmats_output)
    events: list[StandardEvent] = []
    for event_type, filename in RMATS_EVENT_FILES.items():
        events.extend(
            parse_rmats_file(
                directory / filename, event_type, group1_samples, group2_samples
            )
        )
    return events


def is_rmats_directory(path: str | Path) -> bool:
    """Heuristic: a directory containing at least one rMATS JC table."""
    directory = Path(path)
    return any((directory / name).is_file() for name in RMATS_EVENT_FILES.values())
