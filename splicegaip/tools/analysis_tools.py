"""Analysis tools available to the Analyst agent."""

from __future__ import annotations

from typing import Any

from splicegaip.analysis.enrichment import run_enrichment as _run_enrichment_impl
from splicegaip.analysis.statistics import effect_size_summary, recompute_fdr
from splicegaip.splicing.filtering import FilterSettings
from splicegaip.splicing.filtering import filter_significant_events as _filter_events_impl
from splicegaip.splicing.ranking import rank_candidates as _rank_candidates_impl
from splicegaip.tools.context import RunContext


def filter_significant_events(
    context: RunContext,
    fdr_threshold: float | None = None,
    delta_psi_threshold: float | None = None,
    event_types: list[str] | None = None,
) -> str:
    """Filter AS events by FDR and |delta PSI| with quality gating.

    Defaults come from the platform configuration. Events whose p-values
    exist but FDR is missing get FDR recomputed via Benjamini-Hochberg
    first, so filtering never silently drops everything.
    """
    analysis = context.settings.analysis
    settings = FilterSettings(
        fdr_threshold=analysis.fdr_threshold if fdr_threshold is None else fdr_threshold,
        delta_psi_threshold=(
            analysis.delta_psi_threshold if delta_psi_threshold is None else delta_psi_threshold
        ),
        min_support_reads=analysis.min_support_reads,
        min_valid_samples=analysis.min_valid_samples,
    )
    if any(event.p_value is not None and event.fdr is None for event in context.dataset.events):
        recompute_fdr(context.dataset.events)
    significant, report = _filter_events_impl(context.dataset.events, settings)
    if event_types:
        wanted = {str(item).strip().upper() for item in event_types}
        significant = [event for event in significant if event.event_type in wanted]
        # Create a new report with updated counts (FilterReport is frozen)
        from splicegaip.splicing.filtering import FilterReport
        report = FilterReport(
            input_count=report.input_count,
            output_count=len(significant),
            fdr_threshold=report.fdr_threshold,
            delta_psi_threshold=report.delta_psi_threshold,
            min_support_reads=report.min_support_reads,
            min_valid_samples=report.min_valid_samples,
            excluded=dict(report.excluded),
        )
    context.significant_events = significant
    context.filter_report = report
    context.memory.save_events(
        context.project_id, context.dataset.events, {event.event_id for event in significant}
    )
    stats = effect_size_summary(significant)
    message = (
        f"Filtered {report.input_count} events -> {report.output_count} significant events "
        f"(FDR<{settings.fdr_threshold}, |delta PSI|>{settings.delta_psi_threshold}). "
        f"Excluded: {report.excluded or 'none'}. "
        f"Mean |delta PSI| of significant events: {stats['mean_abs_delta_psi']}."
    )
    context.log("bio_analyst", "filter_significant_events", "ok", message)
    return message


def rank_candidates(context: RunContext, top_n: int | None = None) -> str:
    """Rank significant events by the composite candidate score."""
    limit = top_n or context.settings.analysis.top_candidates
    literature = context.knowledge.literature_score(
        context.knowledge.collect_evidence(
            _candidate_gene_names(context), use_pubmed=False, max_per_gene=1
        )
    )
    candidates = _rank_candidates_impl(
        context.significant_events,
        annotated_genes=context.dataset.annotation,
        literature_genes=literature,
    )
    context.candidates = candidates[:limit]
    context.memory.save_candidates(context.project_id, context.candidates)
    top = context.candidates[:5]
    listing = ", ".join(
        f"{item.gene_symbol or item.gene_id}({item.event_type}, score={item.score:.3f})" for item in top
    )
    message = (
        f"Ranked {len(context.significant_events)} significant events; "
        f"top candidates: {listing or 'none'}."
    )
    context.log("bio_analyst", "rank_candidates", "ok", message)
    return message


def run_enrichment(context: RunContext, alpha: float | None = None) -> str:
    """Run functional enrichment for the candidate genes.

    Uses the gene annotation table supplied with the input; when no
    annotation is available the tool reports that enrichment is skipped
    instead of inventing results.
    """
    genes = context.top_genes()
    if not context.dataset.annotation:
        message = (
            "No gene annotation table supplied; functional enrichment skipped. "
            "Provide gene_annotation.tsv (GO/KEGG columns) to enable enrichment."
        )
        context.log("bio_analyst", "run_enrichment", "skipped", message)
        return message
    alpha = alpha if alpha is not None else context.settings.analysis.enrichment_alpha
    results = _run_enrichment_impl(genes, context.dataset.annotation, alpha=alpha)
    context.enrichment = results
    context.memory.save_enrichment(context.project_id, results)
    if not results:
        message = f"Enrichment found no significant terms (alpha={alpha}) among {len(genes)} candidate genes."
        context.log("bio_analyst", "run_enrichment", "ok", message)
        return message
    top = results[:5]
    listing = "; ".join(f"{item.term} [{item.ontology}] (fold={item.fold_enrichment}, FDR={item.fdr})" for item in top)
    message = f"Enriched {len(results)} terms; top: {listing}."
    context.log("bio_analyst", "run_enrichment", "ok", message)
    return message


def _candidate_gene_names(context: RunContext) -> list[str]:
    """Gene symbols for the events that will be ranked (or all genes)."""
    if context.significant_events:
        genes = [event.gene_symbol or event.gene_id for event in context.significant_events]
    else:
        genes = [event.gene_symbol or event.gene_id for event in context.dataset.events]
    return [gene for gene in dict.fromkeys(genes) if gene]


def analysis_summary(context: RunContext) -> dict[str, Any]:
    """Structured summary of the analysis state (used by the report)."""
    stats = effect_size_summary(context.significant_events)
    return {
        "total_events": len(context.dataset.events),
        "significant_events": len(context.significant_events),
        "filter": context.filter_report.as_dict() if context.filter_report else None,
        "effect_size": stats,
        "candidate_count": len(context.candidates),
        "enriched_terms": len(context.enrichment),
        "figures": len(context.figures),
    }
