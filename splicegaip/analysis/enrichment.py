"""Functional enrichment analysis (GO / KEGG) over a local annotation table.

The enrichment test is a standard hypergeometric over-representation test
computed against the background gene set supplied with the annotation
table, so results are fully reproducible and do not require network
access. UniProt / PubMed evidence is layered on separately by the
knowledge module.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

#: Ontology column names accepted in the annotation table.
ONTOLOGY_COLUMNS: tuple[str, ...] = (
    "go_biological_process",
    "go_molecular_function",
    "go_cellular_component",
    "kegg_pathway",
    "reactome_pathway",
    "tf_family",
    "disease_association",
)


@dataclass(frozen=True)
class GeneAnnotation:
    """Functional annotation for one gene."""

    gene_id: str
    gene_symbol: str
    terms: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def terms_for(self, ontology: str) -> tuple[str, ...]:
        return self.terms.get(ontology, ())


def load_gene_annotation(path: str | Path) -> dict[str, GeneAnnotation]:
    """Load a gene annotation table.

    Expected columns: ``gene_id`` (or ``gene_symbol``) plus any of the
    :data:`ONTOLOGY_COLUMNS`; multiple terms per column are separated by
    ``;`` or ``|``.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Annotation table not found: {path}")
    annotations: dict[str, GeneAnnotation] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter="\t"):
            gene_id = str(raw.get("gene_id", "")).strip()
            gene_symbol = str(raw.get("gene_symbol", "")).strip() or gene_id
            if not gene_id and not gene_symbol:
                continue
            terms: dict[str, tuple[str, ...]] = {}
            for ontology in ONTOLOGY_COLUMNS:
                value = str(raw.get(ontology, "") or "").strip()
                if not value or value.upper() in {"NA", "NONE"}:
                    continue
                items = tuple(
                    item.strip()
                    for item in value.replace("|", ";").split(";")
                    if item.strip()
                )
                if items:
                    terms[ontology] = items
            record = GeneAnnotation(gene_id=gene_id or gene_symbol, gene_symbol=gene_symbol, terms=terms)
            annotations[record.gene_id] = record
            if gene_symbol and gene_symbol != record.gene_id:
                annotations[gene_symbol] = record
    return annotations


@dataclass(frozen=True)
class EnrichmentResult:
    """One enriched term."""

    ontology: str
    term: str
    gene_count: int
    background_count: int
    fold_enrichment: float
    p_value: float
    fdr: float
    genes: tuple[str, ...]


def _log_comb(total: int, choose: int) -> float:
    """log C(total, choose) with edge cases."""
    if choose < 0 or choose > total:
        return float("-inf")
    return math.lgamma(total + 1) - math.lgamma(choose + 1) - math.lgamma(total - choose + 1)


def _hypergeom_p_value(successes: int, draws: int, population_successes: int, population: int) -> float:
    """One-sided hypergeometric over-representation p-value (upper tail).

    P(X >= successes) under the hypergeometric model with ``population``
    background genes, ``population_successes`` of them annotated with the
    term, and ``draws`` query genes.
    """
    if population <= 0 or draws <= 0 or population_successes <= 0:
        return 1.0
    if successes <= 0:
        return 1.0
    upper = min(draws, population_successes)
    if successes > upper:
        return 0.0
    total = 0.0
    for value in range(successes, upper + 1):
        log_pmf = (
            _log_comb(population_successes, value)
            + _log_comb(population - population_successes, draws - value)
            - _log_comb(population, draws)
        )
        total += math.exp(log_pmf)
    return min(1.0, total)


def run_enrichment(
    query_genes: Sequence[str],
    annotations: Mapping[str, GeneAnnotation],
    ontologies: Iterable[str] | None = None,
    alpha: float = 0.05,
    min_gene_count: int = 2,
) -> list[EnrichmentResult]:
    """Run hypergeometric over-representation for each ontology.

    :param query_genes: genes selected from the analysis (e.g. top candidates).
    :param annotations: background annotation table (may be keyed by gene id
        and gene symbol; records are de-duplicated for the background).
    :param ontologies: ontologies to test (defaults to all available).
    :param alpha: FDR threshold for reported terms.
    :param min_gene_count: minimum overlapping genes for a reported term.
    """
    query = [gene for gene in dict.fromkeys(query_genes) if gene]
    if not query or not annotations:
        return []

    # De-duplicate the background: the annotation table may register the same
    # record under both gene id and gene symbol.
    unique_records: dict[str, GeneAnnotation] = {}
    for record in annotations.values():
        unique_records.setdefault(record.gene_id, record)
    background_genes = list(unique_records)
    population = len(background_genes)
    query_set = set(query)
    ontology_list = list(ontologies) if ontologies else list(ONTOLOGY_COLUMNS)

    # Map every label (gene id or symbol) to its record so query symbols and
    # background ids refer to the same gene.
    label_to_record: dict[str, GeneAnnotation] = {}
    for record in unique_records.values():
        label_to_record[record.gene_id] = record
        if record.gene_symbol:
            label_to_record.setdefault(record.gene_symbol, record)

    raw_results: list[tuple[str, str, int, int, float, tuple[str, ...]]] = []
    for ontology in ontology_list:
        term_to_genes: dict[str, set[str]] = {}
        for gene_id, record in unique_records.items():
            for term in record.terms_for(ontology):
                term_to_genes.setdefault(term, set()).add(gene_id)
        for term, term_gene_ids in term_to_genes.items():
            # Overlap in record space, reported with the query's labels.
            overlap_labels = sorted(
                gene
                for gene in query
                if (record := label_to_record.get(gene)) is not None
                and record.gene_id in term_gene_ids
            )
            if len(overlap_labels) < min_gene_count:
                continue
            p_value = _hypergeom_p_value(
                successes=len(overlap_labels),
                draws=len(query),
                population_successes=len(term_gene_ids),
                population=population,
            )
            raw_results.append((ontology, term, len(overlap_labels), len(term_gene_ids), p_value, tuple(overlap_labels)))

    # Benjamini-Hochberg across all tested terms.
    ordered = sorted(raw_results, key=lambda item: item[4])
    total = len(ordered)
    fdr_by_index: dict[int, float] = {}
    running = 1.0
    for rank in range(total - 1, -1, -1):
        running = min(running, ordered[rank][4] * total / (rank + 1))
        fdr_by_index[rank] = min(1.0, running)

    results: list[EnrichmentResult] = []
    for rank, (ontology, term, overlap_count, background_count, p_value, genes) in enumerate(ordered):
        fdr = fdr_by_index[rank]
        if fdr > alpha:
            continue
        expected = len(query) * background_count / max(population, 1)
        fold = overlap_count / expected if expected > 0 else float("inf")
        results.append(
            EnrichmentResult(
                ontology=ontology,
                term=term,
                gene_count=overlap_count,
                background_count=background_count,
                fold_enrichment=round(fold, 3),
                p_value=round(p_value, 6),
                fdr=round(fdr, 6),
                genes=genes,
            )
        )
    results.sort(key=lambda item: (item.fdr, -item.gene_count))
    return results
