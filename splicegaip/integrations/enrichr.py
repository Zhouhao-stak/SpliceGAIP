"""Enrichr over-representation analysis through GSEApy.

Why this exists: the built-in :class:`~splicegaip.skills.pathway_enrichment.
PathwayEnrichmentSkill` hand-rolls HTTP calls against several endpoints.
GSEApy is a maintained, citable implementation (Bioinformatics 2023) that
speaks the same Enrichr API and normalises the output for us — so we use it
when it is installed and fall back to the built-in skill otherwise.

The call is network-dependent, so it is always executed with a timeout and
returns ``None`` on any failure.
"""

from __future__ import annotations

import tempfile
from typing import Any, Sequence

from .runner import run_with_timeout, _rows_from_frame  # noqa: PLC2701

#: Enrichr libraries worth querying for a splicing candidate list.
DEFAULT_LIBRARIES: tuple[str, ...] = (
    "GO_Biological_Process_2023",
    "KEGG_2021_Human",
    "Reactome_2022",
)

#: GSEApy 1.x validates the organism against a lowercase lookup table.
ORGANISMS: dict[str, str] = {
    "human": "human",
    "homo sapiens": "human",
    "mouse": "mouse",
    "mus musculus": "mouse",
    "rat": "rat",
    "fly": "fly",
    "drosophila": "fly",
    "yeast": "yeast",
    "zebrafish": "zebrafish",
    "worm": "worm",
}


def backend_available() -> bool:
    try:
        import gseapy  # noqa: F401, PLC0415

        return True
    except Exception:  # noqa: BLE001
        return False


def enrich(
    genes: Sequence[str],
    *,
    organism: str = "human",
    libraries: Sequence[str] | None = None,
    background: Sequence[str] | None = None,
    top_terms: int = 20,
    timeout: float = 12.0,
) -> list[dict[str, Any]] | None:
    """Run over-representation analysis; ``None`` when unavailable/failed.

    Returns normalised rows with the keys used across SpliceGAIP:
    ``term``, ``library``, ``genes``, ``fold_enrichment``, ``p_value``,
    ``fdr`` and ``source``.
    """
    if not genes or not backend_available():
        return None
    wanted = list(dict.fromkeys(str(gene).strip() for gene in genes if str(gene).strip()))
    if len(wanted) < 2:
        return None
    libs = [str(item) for item in (libraries or DEFAULT_LIBRARIES)]
    org = ORGANISMS.get(str(organism).strip().lower(), "Human")

    def _call() -> list[dict[str, Any]]:
        import shutil  # noqa: PLC0415

        import gseapy  # noqa: PLC0415

        # GSEApy keeps a log file open for the whole call, which makes
        # TemporaryDirectory's cleanup fail on Windows. Use a plain temp dir
        # and remove it best-effort instead.
        tmp = tempfile.mkdtemp(prefix="splicegaip-gseapy-")
        try:
            result = gseapy.enrichr(
                gene_list=wanted,
                gene_sets=libs,
                organism=org,
                background=list(background) if background else None,
                outdir=tmp,
                top_term=int(top_terms),
                no_plot=True,
                verbose=False,
            )
            frame = getattr(result, "results", None)
            return _rows_from_frame(frame, limit=max(int(top_terms), 1))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    rows = run_with_timeout(_call, timeout)
    if not rows:
        return None
    return [_normalise(row) for row in rows]


def _normalise(row: dict[str, Any]) -> dict[str, Any]:
    def pick(*keys: str, default: Any = None) -> Any:
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return default

    raw_genes = pick("Genes", "genes", default="")
    if isinstance(raw_genes, str):
        gene_list = [item.strip() for item in raw_genes.replace(";", ",").split(",") if item.strip()]
    elif isinstance(raw_genes, (list, tuple)):
        gene_list = [str(item).strip() for item in raw_genes if str(item).strip()]
    else:
        gene_list = []
    return {
        "term": str(pick("Term", "term", default="")),
        "library": str(pick("Gene_set", "gene_set", "library", default="Enrichr")),
        "ontology": _ontology_of(str(pick("Gene_set", "library", default=""))),
        "genes": tuple(gene_list),
        "gene_count": len(gene_list),
        "fold_enrichment": _as_float(pick("Odds Ratio", "Fold Enrichment", "fold_enrichment")),
        "p_value": _as_float(pick("P-value", "p_value", "pvalue")),
        "fdr": _as_float(pick("Adjusted P-value", "FDR", "fdr")),
        "overlap": str(pick("Overlap", "overlap", default="")),
        "source": "GSEApy/Enrichr",
    }


def _ontology_of(library: str) -> str:
    text = (library or "").upper()
    if text.startswith("GO_") or "GO_" in text or "BIOLOGICAL" in text or "MOLECULAR" in text:
        return "GO"
    if "KEGG" in text:
        return "KEGG"
    if "REACTOME" in text:
        return "Reactome"
    if "WIKI" in text:
        return "WikiPathways"
    return "Enrichr"


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        if number != number:  # NaN
            return None
        return number
    except (TypeError, ValueError):
        return None
