"""Tool registry.

Binds the tool functions to a :class:`RunContext` through explicit
closures (AutoGen's ``FunctionTool`` derives its JSON schema from the
function signature, so wrappers must keep a real signature) and exposes
them as AutoGen ``FunctionTool`` objects, mirroring BioGAIP's tool
registration pattern.
"""

from __future__ import annotations

from autogen_core.tools import FunctionTool

from splicegaip.tools.context import RunContext


def build_tools(context: RunContext) -> dict[str, FunctionTool]:
    """Build the full tool set bound to ``context``."""
    from splicegaip.tools.analysis_tools import (
        filter_significant_events as _filter_events,
        rank_candidates as _rank_candidates,
        run_enrichment as _run_enrichment,
    )
    from splicegaip.tools.data_tools import summarize_dataset as _summarize_dataset
    from splicegaip.tools.knowledge_tools import (
        collect_literature_evidence as _collect_evidence,
        interpret_candidates as _interpret_candidates,
    )
    from splicegaip.tools.report_tools import generate_report as _generate_report
    from splicegaip.tools.viz_tools import generate_figures as _generate_figures

    def summarize_dataset() -> str:
        """Return a compact summary of the loaded dataset (events, samples, groups, validation)."""
        return _summarize_dataset(context)

    def filter_significant_events(
        fdr_threshold: float | None = None,
        delta_psi_threshold: float | None = None,
    ) -> str:
        """Filter AS events by FDR and |delta PSI| with quality gating. Defaults come from the platform configuration."""
        return _filter_events(context, fdr_threshold, delta_psi_threshold)

    def rank_candidates(top_n: int | None = None) -> str:
        """Rank significant events by the composite candidate score (significance, effect size, biology, literature)."""
        return _rank_candidates(context, top_n)

    def run_enrichment(alpha: float | None = None) -> str:
        """Run GO/KEGG over-representation analysis for candidate genes using the supplied annotation table."""
        return _run_enrichment(context, alpha)

    def generate_figures(output_dir: str | None = None) -> str:
        """Generate the publication figure set (volcano, event composition, PSI heatmap, PSI distribution, candidate ranking, enrichment) as PNG and SVG."""
        return _generate_figures(context, output_dir)

    def collect_literature_evidence(genes: list[str] | None = None, max_per_gene: int = 2) -> str:
        """Collect literature evidence for candidate genes from the curated knowledge base, PubMed and the vector store."""
        return _collect_evidence(context, genes, max_per_gene)

    def interpret_candidates() -> str:
        """Produce the evidence-grounded biological interpretation of the top candidate events."""
        return _interpret_candidates(context)

    def generate_report(output_dir: str | None = None) -> str:
        """Generate the scientific report (Summary/Methods/Results/Figures/Interpretation/References) in HTML and PDF."""
        return _generate_report(context, output_dir)

    functions = [
        summarize_dataset,
        filter_significant_events,
        rank_candidates,
        run_enrichment,
        generate_figures,
        collect_literature_evidence,
        interpret_candidates,
        generate_report,
    ]
    return {
        function.__name__: FunctionTool(function, description=function.__doc__ or "")
        for function in functions
    }


__all__ = ["build_tools"]
