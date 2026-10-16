"""MAJIQ output parser.

MAJIQ produces per-sample ``.vo``/``.psi`` files plus a combined TSV from
``majiq build``/``majiq deltapsi``. This parser reads the standard MAJIQ
TSV export with columns::

    gene  event  type  pos  strand  E(PSI)  dPSI  P(dPSI)  ...

and maps MAJIQ event types onto the SpliceGAIP vocabulary.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from splicegaip.splicing.schema import StandardEvent, _to_float

#: MAJIQ event-type names to the SpliceGAIP vocabulary.
MAJIQ_EVENT_TYPE_MAP: dict[str, str] = {
    "cassette": "SE",
    "alt3": "A3SS",
    "alt5": "A5SS",
    "ir": "RI",
    "mic": "MXE",
    "tandem3": "A3SS",
    "bleeding": "SE",
}


def parse_majiq_file(path: str | Path) -> list[StandardEvent]:
    """Parse a MAJIQ TSV export into standardized events."""
    path = Path(path)
    if not path.is_file():
        return []
    events: list[StandardEvent] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter="\t"):
            gene = str(raw.get("gene", "")).strip()
            event = str(raw.get("event", "")).strip()
            majiq_type = str(raw.get("type", "")).strip().lower()
            delta = _to_float(raw.get("dPSI"))
            p_value = _to_float(raw.get("P(dPSI)")) or _to_float(raw.get("pval"))
            psi = _to_float(raw.get("E(PSI)")) or _to_float(raw.get("mean_psi"))
            events.append(
                StandardEvent(
                    event_id=event or f"{majiq_type}:{gene}",
                    gene_id=gene,
                    gene_symbol=gene,
                    event_type=MAJIQ_EVENT_TYPE_MAP.get(majiq_type, majiq_type.upper() or "SE"),
                    chromosome=str(raw.get("chr", "")).strip(),
                    strand=str(raw.get("strand", "")).strip(),
                    genomic_coordinates=str(raw.get("pos", "")).strip(),
                    coordinate_system="majiq",
                    source_tool="MAJIQ",
                    mean_psi_group1=None,
                    mean_psi_group2=psi,
                    delta_psi=delta,
                    p_value=p_value,
                    fdr=None,
                    valid_sample_count=None,
                )
            )
    return events


def is_majiq_file(path: str | Path) -> bool:
    """Heuristic: a TSV whose header contains MAJIQ's ``dPSI``/``P(dPSI)`` columns."""
    path = Path(path)
    if not path.is_file() or path.suffix.lower() not in {".tsv", ".txt"}:
        return False
    try:
        header = path.read_text(encoding="utf-8-sig").splitlines()[0]
    except (OSError, IndexError):
        return False
    columns = {column.strip() for column in header.split("\t")}
    return "dPSI" in columns or "P(dPSI)" in columns
