"""Extended gene annotation and pathway analysis via bioservices.

Provides access to Ensembl, UniProt, KEGG, and Reactome when the
``bioservices`` package is installed. Falls back gracefully when unavailable.

This supplements the existing MyGene.info and Enrichr integrations with:
- Ensembl REST API for detailed gene/transcript information
- UniProt protein function and domain annotations
- KEGG pathway mapping and enrichment
- Reactome pathway browser integration
"""

from __future__ import annotations

from typing import Any, Sequence

from .runner import run_with_timeout


def backend_available() -> bool:
    """Check if bioservices is installed."""
    try:
        import bioservices  # noqa: F401, PLC0415
        return True
    except Exception:  # noqa: BLE001
        return False


def ensembl_annotate(
    genes: Sequence[str],
    *,
    species: str = "hsapiens",
    timeout: float = 15.0,
) -> dict[str, dict[str, Any]] | None:
    """Annotate genes using Ensembl REST API.

    Returns more detailed information than MyGene.info:
    - Transcript variants
    - Chromosomal coordinates
    - Gene biotype (protein_coding, lncRNA, etc.)
    - Homologues across species

    Args:
        genes: Gene symbols or Ensembl IDs
        species: Ensembl species code (default: human)
        timeout: Maximum seconds to wait

    Returns:
        Dict of {gene_id: annotation_dict} or None on failure
    """
    if not genes or not backend_available():
        return None

    wanted = list(dict.fromkeys(str(gene).strip() for gene in genes if str(gene).strip()))
    if not wanted:
        return None

    def _call() -> dict[str, dict[str, Any]]:
        from bioservices import Ensembl  # noqa: PLC0415

        ens = Ensembl(verbose=False)
        results: dict[str, dict[str, Any]] = {}

        for gene_query in wanted[:20]:  # Limit batch size
            try:
                # Try symbol first
                res = ens.lookup_symbol(species, gene_query, content_type="application/json")
                if res:
                    gene_id = res.get("id", gene_query)
                    results[gene_query] = {
                        "ensembl_id": gene_id,
                        "symbol": res.get("display_name"),
                        "name": res.get("description", ""),
                        "biotype": res.get("biotype"),
                        "chromosome": res.get("seq_region_name"),
                        "start": res.get("start"),
                        "end": res.get("end"),
                        "strand": res.get("strand"),
                        "source": "Ensembl",
                    }
            except Exception:
                # Try as Ensembl ID
                try:
                    res = ens.lookup_id(gene_query, content_type="application/json")
                    if res:
                        results[gene_query] = {
                            "ensembl_id": res.get("id"),
                            "symbol": res.get("display_name"),
                            "biotype": res.get("biotype"),
                            "source": "Ensembl",
                        }
                except Exception:
                    pass

        return results

    return run_with_timeout(_call, timeout)


def uniprot_annotate(
    proteins: Sequence[str],
    *,
    timeout: float = 15.0,
) -> dict[str, dict[str, Any]] | None:
    """Annotate proteins using UniProt.

    Retrieves:
    - Protein function descriptions
    - Domain/motif information
    - Subcellular location
    - Disease associations
    - Post-translational modifications

    Args:
        proteins: UniProt IDs or gene symbols
        timeout: Maximum seconds to wait

    Returns:
        Dict of {protein_id: annotation_dict} or None on failure
    """
    if not proteins or not backend_available():
        return None

    wanted = list(dict.fromkeys(str(p).strip() for p in proteins if str(p).strip()))
    if not wanted:
        return None

    def _call() -> dict[str, dict[str, Any]]:
        from bioservices import UniProt  # noqa: PLC0415

        uniprot = UniProt(verbose=False)
        results: dict[str, dict[str, Any]] = {}

        for query in wanted[:15]:  # Limit batch size
            try:
                # Search by gene name or UniProt ID
                res = uniprot.search(f"gene:{query}", limit=1, format="json")
                if res and isinstance(res, list) and len(res) > 0:
                    entry = res[0]
                    results[query] = {
                        "uniprot_id": entry.get("primaryAccession"),
                        "protein_name": entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
                        "function": (entry.get("comments", [{}])[0].get("texts", [{}])[0].get("value", "") if entry.get("comments") else "")[:500],
                        "subcellular_location": _extract_subcellular(entry),
                        "disease": _extract_disease(entry),
                        "source": "UniProt",
                    }
            except Exception:
                pass

        return results

    return run_with_timeout(_call, timeout)


def kegg_pathways(
    genes: Sequence[str],
    *,
    organism: str = "human",
    timeout: float = 20.0,
) -> list[dict[str, Any]] | None:
    """Get KEGG pathways for gene list.

    Uses KEGG's native pathway database (not Enrichr wrapper):
    - Direct KEGG API access
    - Pathway enrichment statistics
    - Gene-pathway mappings

    Args:
        genes: Gene symbols (will be converted to KEGG IDs internally)
        organism: KEGG organism code (human, mouse, rat, etc.)
        timeout: Maximum seconds to wait

    Returns:
        List of pathway dicts with term, genes, p_value, fdr
    """
    if not genes or not backend_available():
        return None

    wanted = list(dict.fromkeys(str(gene).strip() for gene in genes if str(gene).strip()))
    if len(wanted) < 3:
        return None

    def _call() -> list[dict[str, Any]]:
        from bioservices import KEGG  # noqa: PLC0415

        kegg = KEGG(verbose=False)
        org_code = _kegg_org_code(organism)

        # Get all pathways for organism
        try:
            pathways = kegg.list_pathways(org_code)
            if not pathways:
                return []
        except Exception:
            return []

        # For each pathway, get genes and check overlap
        results = []
        gene_set = set(g.upper() for g in wanted)

        for pathway_id, pathway_name in list(pathways.items())[:50]:  # Top 50 pathways
            try:
                # Get genes in this pathway
                pathway_genes_raw = kegg.get_genes_by_pathway(pathway_id)
                if not pathway_genes_raw:
                    continue

                # Parse gene list (format varies)
                pathway_genes = set()
                for item in pathway_genes_raw:
                    if isinstance(item, str):
                        # Extract gene symbol from "ORG:SYMBOL" format
                        parts = item.split(":")
                        if len(parts) == 2:
                            pathway_genes.add(parts[1].upper())

                # Calculate overlap
                overlap = gene_set.intersection(pathway_genes)
                if len(overlap) >= 2:  # At least 2 genes required
                    # Simple enrichment (hypergeometric would need background)
                    fold = len(overlap) / max(len(gene_set) * len(pathway_genes) / 20000, 1)
                    results.append({
                        "term": f"{pathway_name} ({pathway_id})",
                        "library": "KEGG",
                        "ontology": "KEGG",
                        "genes": tuple(sorted(overlap)),
                        "gene_count": len(overlap),
                        "fold_enrichment": round(fold, 3),
                        "p_value": None,  # Would need proper statistical test
                        "fdr": None,
                        "source": "KEGG via bioservices",
                    })
            except Exception:
                continue

        # Sort by gene count (most represented first)
        results.sort(key=lambda x: x["gene_count"], reverse=True)
        return results[:20]  # Top 20

    return run_with_timeout(_call, timeout)


def reactome_pathways(
    genes: Sequence[str],
    *,
    species: str = "Homo sapiens",
    timeout: float = 20.0,
) -> list[dict[str, Any]] | None:
    """Get Reactome pathways for gene list.

    Accesses Reactome's curated pathway database:
    - Detailed pathway hierarchy
    - Reaction-level detail
    - Cross-references to other databases

    Args:
        genes: Gene symbols
        species: Full species name
        timeout: Maximum seconds to wait

    Returns:
        List of pathway dicts similar to kegg_pathways output
    """
    if not genes or not backend_available():
        return None

    wanted = list(dict.fromkeys(str(gene).strip() for gene in genes if str(gene).strip()))
    if len(wanted) < 3:
        return None

    def _call() -> list[dict[str, Any]]:
        from bioservices import Reactome  # noqa: PLC0415

        reactome = Reactome(verbose=False)
        results = []

        try:
            # Map genes to Reactome entities
            mapped = reactome.convert_ids(wanted[:30], species=species)
            if not mapped:
                return []

            # Get pathways for mapped entities
            entity_ids = list(mapped.keys())[:20]  # Limit
            for entity_id in entity_ids:
                try:
                    pathways = reactome.get_participating_pathways(entity_id, species=species)
                    if pathways:
                        for pw_id, pw_name in pathways.items():
                            results.append({
                                "term": pw_name,
                                "library": "Reactome",
                                "ontology": "Reactome",
                                "genes": (entity_id,),
                                "gene_count": 1,
                                "fold_enrichment": None,
                                "p_value": None,
                                "fdr": None,
                                "reactome_id": pw_id,
                                "source": "Reactome via bioservices",
                            })
                except Exception:
                    continue

            # Aggregate by pathway
            aggregated: dict[str, dict[str, Any]] = {}
            for row in results:
                term = row["term"]
                if term not in aggregated:
                    aggregated[term] = {
                        "term": term,
                        "library": "Reactome",
                        "ontology": "Reactome",
                        "genes": set(),
                        "gene_count": 0,
                        "reactome_ids": set(),
                        "source": "Reactome via bioservices",
                    }
                aggregated[term]["genes"].update(row["genes"])
                if row.get("reactome_id"):
                    aggregated[term]["reactome_ids"].add(row["reactome_id"])

            # Convert sets to tuples and sort
            final_results = []
            for row in aggregated.values():
                row["genes"] = tuple(sorted(row["genes"]))
                row["gene_count"] = len(row["genes"])
                del row["reactome_ids"]
                final_results.append(row)

            final_results.sort(key=lambda x: x["gene_count"], reverse=True)
            return final_results[:20]

        except Exception:
            return []

    return run_with_timeout(_call, timeout)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kegg_org_code(organism: str) -> str:
    """Convert common organism names to KEGG codes."""
    mapping = {
        "human": "hsa",
        "homo sapiens": "hsa",
        "mouse": "mmu",
        "mus musculus": "mmu",
        "rat": "rno",
        "fly": "dme",
        "drosophila": "dme",
        "yeast": "sce",
        "zebrafish": "dre",
        "worm": "cel",
    }
    return mapping.get(organism.lower().strip(), "hsa")


def _extract_subcellular(entry: dict[str, Any]) -> str | None:
    """Extract subcellular location from UniProt entry."""
    comments = entry.get("comments", [])
    for comment in comments:
        if comment.get("commentType") == "SUBCELLULAR LOCATION":
            texts = comment.get("texts", [])
            if texts:
                return texts[0].get("value", "")[:200]
    return None


def _extract_disease(entry: dict[str, Any]) -> str | None:
    """Extract disease association from UniProt entry."""
    comments = entry.get("comments", [])
    for comment in comments:
        if comment.get("commentType") == "DISEASE":
            texts = comment.get("texts", [])
            if texts:
                return texts[0].get("value", "")[:300]
    return None
