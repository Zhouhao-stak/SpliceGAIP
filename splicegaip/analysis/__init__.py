"""Analysis subpackage: statistics, enrichment and visualization."""

from splicegaip.analysis.enrichment import (
    EnrichmentResult,
    GeneAnnotation,
    load_gene_annotation,
    run_enrichment,
)
from splicegaip.analysis.statistics import (
    benjamini_hochberg,
    chi_square_p_value,
    effect_size_summary,
    recompute_fdr,
)
from splicegaip.analysis.visualization import (
    FIGURE_SPECS,
    FigureResult,
    generate_all_figures,
)

__all__ = [
    "EnrichmentResult",
    "FIGURE_SPECS",
    "FigureResult",
    "GeneAnnotation",
    "benjamini_hochberg",
    "chi_square_p_value",
    "effect_size_summary",
    "generate_all_figures",
    "load_gene_annotation",
    "recompute_fdr",
    "run_enrichment",
]
