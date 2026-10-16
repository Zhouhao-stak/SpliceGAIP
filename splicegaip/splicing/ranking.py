"""Candidate prioritization for AS events.

Composite score (per the SpliceGAIP design):

* 0.4 statistical significance  (-log10 FDR, normalized)
* 0.3 effect size               (|delta PSI|)
* 0.2 biological relevance      (annotation coverage of the gene)
* 0.1 literature evidence       (hits in the knowledge base)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from splicegaip.splicing.schema import StandardEvent

WEIGHT_SIGNIFICANCE = 0.4
WEIGHT_EFFECT = 0.3
WEIGHT_BIOLOGY = 0.2
WEIGHT_LITERATURE = 0.1


@dataclass(frozen=True)
class RankedCandidate:
    """One ranked candidate event with its score decomposition."""

    event_id: str
    gene_id: str
    gene_symbol: str
    event_type: str
    delta_psi: float | None
    fdr: float | None
    score: float
    significance_component: float
    effect_component: float
    biology_component: float
    literature_component: float
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "gene_id": self.gene_id,
            "gene_symbol": self.gene_symbol,
            "event_type": self.event_type,
            "delta_PSI": self.delta_psi,
            "FDR": self.fdr,
            "score": round(self.score, 4),
            "significance_component": round(self.significance_component, 4),
            "effect_component": round(self.effect_component, 4),
            "biology_component": round(self.biology_component, 4),
            "literature_component": round(self.literature_component, 4),
            "evidence": list(self.evidence),
        }


def _normalized_significance(fdr: float | None, floor: float = 1e-300) -> float:
    """Map FDR to (0, 1]: smaller FDR -> closer to 1."""
    if fdr is None:
        return 0.0
    value = min(max(-math.log10(max(fdr, floor)) / 10.0, 0.0), 1.0)
    return value


def _normalized_effect(delta_psi: float | None) -> float:
    """Map |delta PSI| to (0, 1]: |dPSI| >= 0.5 saturates at 1."""
    if delta_psi is None:
        return 0.0
    return min(abs(delta_psi) / 0.5, 1.0)


def _biology_component(event: StandardEvent, annotated_genes: Mapping[str, object]) -> float:
    """Annotation coverage of the gene (GO/KEGG/pathway terms available)."""
    gene = event.gene_symbol or event.gene_id
    if gene and gene in annotated_genes:
        return 1.0
    return 0.0


def _literature_component(event: StandardEvent, literature_genes: Mapping[str, object]) -> float:
    """Literature evidence count for the gene, capped at 5 records -> 1.0."""
    gene = event.gene_symbol or event.gene_id
    hits = literature_genes.get(gene) if gene else None
    if not hits:
        return 0.0
    count = hits if isinstance(hits, int) else len(hits)  # type: ignore[arg-type]
    return min(float(count) / 5.0, 1.0)


def rank_candidates(
    events: Sequence[StandardEvent],
    annotated_genes: Mapping[str, object] | None = None,
    literature_genes: Mapping[str, object] | None = None,
) -> list[RankedCandidate]:
    """Rank events by the composite score (descending)."""
    annotated_genes = annotated_genes or {}
    literature_genes = literature_genes or {}
    ranked: list[RankedCandidate] = []
    for event in events:
        significance = _normalized_significance(event.fdr)
        effect = _normalized_effect(event.delta_psi)
        biology = _biology_component(event, annotated_genes)
        literature = _literature_component(event, literature_genes)
        score = (
            WEIGHT_SIGNIFICANCE * significance
            + WEIGHT_EFFECT * effect
            + WEIGHT_BIOLOGY * biology
            + WEIGHT_LITERATURE * literature
        )
        gene = event.gene_symbol or event.gene_id
        evidence: list[str] = []
        if event.fdr is not None:
            evidence.append(f"FDR={event.fdr:.3g}")
        if event.delta_psi is not None:
            evidence.append(f"dPSI={event.delta_psi:+.3f}")
        if biology:
            evidence.append("functional annotation available")
        if literature:
            evidence.append("literature evidence available")
        ranked.append(
            RankedCandidate(
                event_id=event.event_id,
                gene_id=event.gene_id,
                gene_symbol=event.gene_symbol,
                event_type=event.event_type,
                delta_psi=event.delta_psi,
                fdr=event.fdr,
                score=round(score, 6),
                significance_component=significance,
                effect_component=effect,
                biology_component=biology,
                literature_component=literature,
                evidence=tuple(evidence),
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def top_candidate_genes(candidates: Iterable[RankedCandidate], limit: int = 20) -> list[str]:
    """Unique gene list from the top candidates, preserving rank order."""
    genes: list[str] = []
    for candidate in candidates:
        gene = candidate.gene_symbol or candidate.gene_id
        if gene and gene not in genes:
            genes.append(gene)
        if len(genes) >= limit:
            break
    return genes
