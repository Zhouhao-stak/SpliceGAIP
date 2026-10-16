"""LeafCutter output parser.

LeafCutter differential splicing produces
``<group1>_<group2>_cluster_significance.txt`` with columns::

    chrom  start  end  strand  cluster  nsamples  dPsi  p  p.adjust  ...

Each row is an intron-cluster event (effectively a skipped-exon style
event). Coordinates are 1-based BED-style.
"""

from __future__ import annotations

import csv
from pathlib import Path

from splicegaip.splicing.schema import StandardEvent, _to_float

#: Column names accepted for each standardized field.
_DELTA_KEYS = ("dPsi", "dPSI", "delta_psi")
_PVALUE_KEYS = ("p", "pval", "p_value")
_FDR_KEYS = ("p.adjust", "padj", "FDR", "fdr")


def _first(raw: dict[str, str], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in raw:
            return _to_float(raw.get(key))
    return None


def parse_leafcutter_file(path: str | Path) -> list[StandardEvent]:
    """Parse a LeafCutter cluster-significance table into standardized events."""
    path = Path(path)
    if not path.is_file():
        return []
    events: list[StandardEvent] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter="\t"):
            cluster = str(raw.get("cluster", "")).strip()
            chromosome = str(raw.get("chrom", raw.get("chr", ""))).strip()
            start = str(raw.get("start", "")).strip()
            end = str(raw.get("end", "")).strip()
            strand = str(raw.get("strand", "")).strip()
            gene_hint = str(raw.get("gene", raw.get("gene_id", ""))).strip()
            events.append(
                StandardEvent(
                    event_id=f"LC:{cluster or f'{chromosome}:{start}-{end}'}",
                    gene_id=gene_hint or cluster,
                    gene_symbol=gene_hint or cluster,
                    event_type="SE",
                    chromosome=chromosome,
                    strand=strand,
                    genomic_coordinates=f"{chromosome}:{start}-{end}",
                    coordinate_system="1-based-inclusive",
                    source_tool="LeafCutter",
                    mean_psi_group1=None,
                    mean_psi_group2=None,
                    delta_psi=_first(raw, _DELTA_KEYS),
                    p_value=_first(raw, _PVALUE_KEYS),
                    fdr=_first(raw, _FDR_KEYS),
                    valid_sample_count=None,
                )
            )
    return events


def is_leafcutter_file(path: str | Path) -> bool:
    """Heuristic: filename contains ``cluster_significance``."""
    return "cluster_significance" in Path(path).name
