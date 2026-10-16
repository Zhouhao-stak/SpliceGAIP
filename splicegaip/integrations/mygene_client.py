"""Gene annotation through the official MyGene.info client.

Replaces the hand-rolled REST call in
:class:`~splicegaip.skills.gene_annotation.GeneAnnotationSkill` when the
``mygene`` package is installed: same data source, maintained client, proper
batch querying (one request for all candidate genes instead of one each).

Network-dependent, timeout-guarded, returns ``None`` on failure.
"""

from __future__ import annotations

from typing import Any, Sequence

from .runner import run_with_timeout

FIELDS: tuple[str, ...] = (
    "symbol",
    "name",
    "ensembl.gene",
    "entrezgene",
    "uniprot",
    "type_of_gene",
    "summary",
)


def backend_available() -> bool:
    try:
        import mygene  # noqa: F401, PLC0415

        return True
    except Exception:  # noqa: BLE001
        return False


def annotate(
    genes: Sequence[str],
    *,
    scopes: Sequence[str] | None = None,
    timeout: float = 10.0,
) -> dict[str, dict[str, Any]] | None:
    """Annotate ``genes``; returns ``{query: {...}}`` or ``None`` on failure."""
    if not genes or not backend_available():
        return None
    wanted = list(dict.fromkeys(str(gene).strip() for gene in genes if str(gene).strip()))
    if not wanted:
        return None

    def _call() -> dict[str, dict[str, Any]]:
        import mygene  # noqa: PLC0415

        client = mygene.MyGeneInfo()
        hits = client.querymany(
            wanted,
            scopes=list(scopes) if scopes else "symbol,ensembl.gene,entrezgene",
            fields=list(FIELDS),
            species="human",
            returnall=False,
        )
        return {str(hit.get("query")): _clean(hit) for hit in hits if isinstance(hit, dict)}

    result = run_with_timeout(_call, timeout)
    if not result:
        return None
    return result


def _clean(hit: dict[str, Any]) -> dict[str, Any]:
    ensembl = hit.get("ensembl") or {}
    if isinstance(ensembl, list) and ensembl:
        ensembl = ensembl[0]
    uniprot = hit.get("uniprot")
    if isinstance(uniprot, dict):
        uniprot = uniprot.get("Swiss-Prot") or uniprot.get("TrEMBL")
        if isinstance(uniprot, list):
            uniprot = uniprot[0] if uniprot else None
    return {
        "query": hit.get("query"),
        "symbol": hit.get("symbol"),
        "name": hit.get("name"),
        "ensembl_gene": ensembl.get("gene") if isinstance(ensembl, dict) else None,
        "entrez": hit.get("entrezgene"),
        "uniprot": uniprot,
        "gene_type": hit.get("type_of_gene"),
        "summary": (hit.get("summary") or "")[:600] or None,
        "not_found": bool(hit.get("notfound")),
        "source": "MyGene.info",
    }
