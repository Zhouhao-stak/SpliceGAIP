"""Visualization tool available to the Analyst agent."""

from __future__ import annotations

from splicegaip.analysis.visualization import generate_all_figures
from splicegaip.tools.context import RunContext


def generate_figures(context: RunContext, output_dir: str | None = None) -> str:
    """Generate the publication figure set (PNG 300 DPI + SVG).

    Figures: splicing volcano plot, event-type composition, per-sample
    PSI heatmap, PSI distribution by group, candidate ranking, and
    functional enrichment. Missing data yields a labeled placeholder
    figure rather than fabricated content.
    """
    directory = output_dir or str(context.output_dir / "figures")
    figures = generate_all_figures(
        context.dataset.events,
        context.dataset.samples,
        context.candidates,
        context.enrichment,
        directory,
        fdr_threshold=context.settings.analysis.fdr_threshold,
        delta_psi_threshold=context.settings.analysis.delta_psi_threshold,
    )
    context.figures = figures
    for figure in figures:
        context.memory.save_artifact(context.project_id, f"figure:{figure.name}", str(figure.png_path))
    listing = ", ".join(f"{figure.name}({figure.title})" for figure in figures)
    message = f"Generated {len(figures)} figures into {directory}: {listing}."
    context.log("bio_analyst", "generate_figures", "ok", message)
    return message
