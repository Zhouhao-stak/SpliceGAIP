"""Visualization engine.

Generates publication-style figures with matplotlib (Agg backend) and
saves each figure as both PNG (300 DPI) and SVG, following the output
conventions of the SplicingNexus figure studio. All figures are derived
from computed results only — missing data is reported, never faked.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from splicegaip.analysis.enrichment import EnrichmentResult
from splicegaip.splicing.ranking import RankedCandidate
from splicegaip.splicing.schema import SampleMetadata, StandardEvent

#: Colorblind-safe palette (Okabe-Ito).
COLOR_PRIMARY = "#0072B2"
COLOR_SECONDARY = "#D55E00"
COLOR_NEUTRAL = "#999999"
COLOR_HIGHLIGHT = "#CC79A7"
COLOR_GRID = "#DDDDDD"

plt.rcParams.update(
    {
        "figure.dpi": 100,
        "savefig.dpi": 300,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": COLOR_GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
    }
)


@dataclass(frozen=True)
class FigureResult:
    """One generated figure."""

    name: str
    title: str
    png_path: Path
    svg_path: Path
    caption: str


def _save(fig: Figure, output_dir: Path, name: str, title: str, caption: str) -> FigureResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / f"{name}.png"
    svg_path = output_dir / f"{name}.svg"
    fig.savefig(png_path, format="png", bbox_inches="tight", facecolor="white")
    fig.savefig(svg_path, format="svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return FigureResult(name=name, title=title, png_path=png_path, svg_path=svg_path, caption=caption)


def plot_volcano(
    events: Sequence[StandardEvent],
    output_dir: Path,
    fdr_threshold: float = 0.05,
    delta_psi_threshold: float = 0.1,
) -> FigureResult:
    """Volcano plot of delta PSI vs -log10(FDR) over all events."""
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    points = [
        (event.delta_psi, event.fdr)
        for event in events
        if event.delta_psi is not None and event.fdr is not None
    ]
    if not points:
        ax.text(0.5, 0.5, "No events with both delta PSI and FDR", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, output_dir, "volcano", "Splicing volcano plot", "placeholder")
    deltas = np.array([point[0] for point in points])
    fdrs = np.array([max(point[1], 1e-300) for point in points])
    neg_log_fdr = -np.log10(fdrs)
    significant = (fdrs < fdr_threshold) & (np.abs(deltas) > delta_psi_threshold)
    ax.scatter(deltas[~significant], neg_log_fdr[~significant], s=14, c=COLOR_NEUTRAL, alpha=0.55, label="not significant", linewidths=0)
    ax.scatter(deltas[significant], neg_log_fdr[significant], s=18, c=COLOR_SECONDARY, alpha=0.85, label=f"FDR<{fdr_threshold} & |dPSI|>{delta_psi_threshold}", linewidths=0)
    ax.axhline(-np.log10(fdr_threshold), color=COLOR_PRIMARY, lw=0.9, ls="--")
    ax.axvline(delta_psi_threshold, color=COLOR_PRIMARY, lw=0.9, ls="--")
    ax.axvline(-delta_psi_threshold, color=COLOR_PRIMARY, lw=0.9, ls="--")
    ax.set_xlabel("delta PSI (group2 - group1)")
    ax.set_ylabel("-log10(FDR)")
    ax.set_title(f"Splicing volcano plot (n={len(points)} events)")
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    return _save(
        fig,
        output_dir,
        "volcano",
        "Splicing volcano plot",
        f"Delta PSI versus -log10(FDR) for {len(points)} AS events; "
        f"{int(significant.sum())} events pass FDR<{fdr_threshold} and |delta PSI|>{delta_psi_threshold}.",
    )


def plot_event_type_counts(events: Sequence[StandardEvent], output_dir: Path) -> FigureResult:
    """Bar chart of event counts per AS event type."""
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
    if not counts:
        ax.text(0.5, 0.5, "No events", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, output_dir, "event_type_counts", "Event type composition", "placeholder")
    labels = sorted(counts)
    values = [counts[label] for label in labels]
    ax.bar(labels, values, color=COLOR_PRIMARY, alpha=0.85)
    for index, value in enumerate(values):
        ax.text(index, value, str(value), ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("Event type")
    ax.set_ylabel("Event count")
    ax.set_title("Alternative splicing event composition")
    return _save(
        fig,
        output_dir,
        "event_type_counts",
        "Event type composition",
        "Counts of detected AS events by event type (SE/MXE/A5SS/A3SS/RI).",
    )


def plot_psi_heatmap(
    events: Sequence[StandardEvent],
    samples: Sequence[SampleMetadata],
    output_dir: Path,
    top_n: int = 25,
) -> FigureResult:
    """Heatmap of per-sample PSI for the top |delta PSI| events."""
    fig, ax = plt.subplots(figsize=(7.6, 6.4))
    sample_ids = [sample.sample_id for sample in samples]
    group_by_sample = {sample.sample_id: sample.group for sample in samples}
    ranked = sorted(
        (event for event in events if event.psi_by_sample),
        key=lambda event: abs(event.delta_psi or 0.0),
        reverse=True,
    )[:top_n]
    if not ranked or not sample_ids:
        ax.text(0.5, 0.5, "No per-sample PSI values available", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, output_dir, "psi_heatmap", "PSI heatmap", "placeholder")
    matrix = np.full((len(ranked), len(sample_ids)), np.nan)
    for row, event in enumerate(ranked):
        for column, sample_id in enumerate(sample_ids):
            matrix[row, column] = event.psi_by_sample.get(sample_id, np.nan)
    masked = np.ma.masked_invalid(matrix)
    cmap = plt.get_cmap("viridis").with_extremes(bad="#F0F0F0")
    image = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(sample_ids)))
    ax.set_xticklabels(sample_ids, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(ranked)))
    ax.set_yticklabels(
        [f"{event.gene_symbol or event.gene_id} ({event.event_type})" for event in ranked],
        fontsize=7,
    )
    for column, sample_id in enumerate(sample_ids):
        group = group_by_sample.get(sample_id, "")
        ax.text(
            column,
            -0.9,
            group,
            rotation=45,
            ha="right",
            fontsize=7,
            color=COLOR_SECONDARY if group else COLOR_NEUTRAL,
        )
    ax.set_title(f"PSI heatmap (top {len(ranked)} events by |delta PSI|)")
    ax.grid(False)
    bar = fig.colorbar(image, ax=ax, shrink=0.7)
    bar.set_label("PSI")
    return _save(
        fig,
        output_dir,
        "psi_heatmap",
        "PSI heatmap",
        f"Per-sample PSI values for the top {len(ranked)} events ranked by |delta PSI|; "
        "sample group labels are shown above the columns.",
    )


def plot_psi_distribution(
    events: Sequence[StandardEvent],
    samples: Sequence[SampleMetadata],
    output_dir: Path,
    top_n: int = 8,
) -> FigureResult:
    """Per-event PSI distributions split by group (box + strip)."""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), sharey=False)
    sample_ids = [sample.sample_id for sample in samples]
    groups = sorted({sample.group for sample in samples})
    group_colors = {groups[0]: COLOR_PRIMARY, groups[-1]: COLOR_SECONDARY} if groups else {}
    ranked = sorted(
        (event for event in events if event.psi_by_sample),
        key=lambda event: abs(event.delta_psi or 0.0),
        reverse=True,
    )[:top_n]
    if not ranked or len(groups) < 2:
        for ax in axes:
            ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center")
            ax.set_axis_off()
        return _save(fig, output_dir, "psi_distribution", "PSI distribution", "placeholder")
    for ax, group in zip(axes, groups[:2]):
        group_samples = [sample.sample_id for sample in samples if sample.group == group]
        data = []
        labels = []
        for event in ranked:
            values = [event.psi_by_sample[sample] for sample in group_samples if sample in event.psi_by_sample]
            if values:
                data.append(values)
                labels.append(f"{event.gene_symbol or event.gene_id}\n{event.event_type}")
        if data:
            box = ax.boxplot(data, patch_artist=True, widths=0.55, showfliers=False)
            for patch in box["boxes"]:
                patch.set_facecolor(group_colors.get(group, COLOR_NEUTRAL))
                patch.set_alpha(0.45)
            for index, values in enumerate(data, start=1):
                ax.scatter(
                    [index + (index % 2) * 0.12 - 0.12] * len(values),
                    values,
                    s=16,
                    color=group_colors.get(group, COLOR_NEUTRAL),
                    alpha=0.9,
                    zorder=3,
                    linewidths=0,
                )
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_ylim(-0.05, 1.05)
        ax.set_title(f"Group: {group}")
        ax.set_ylabel("PSI")
    fig.suptitle("PSI distribution of top differential events by group", y=1.02)
    fig.tight_layout()
    return _save(
        fig,
        output_dir,
        "psi_distribution",
        "PSI distribution",
        "Per-sample PSI distributions for the top differential events, split by experimental group.",
    )


def plot_candidate_ranking(
    candidates: Sequence[RankedCandidate],
    output_dir: Path,
    top_n: int = 15,
) -> FigureResult:
    """Horizontal bar chart of composite candidate scores."""
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    top = list(candidates)[:top_n]
    if not top:
        ax.text(0.5, 0.5, "No candidates", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, output_dir, "candidate_ranking", "Candidate ranking", "placeholder")
    labels = [f"{item.gene_symbol or item.gene_id} ({item.event_type})" for item in top][::-1]
    scores = [item.score for item in top][::-1]
    colors = [COLOR_SECONDARY if item.score >= 0.6 else COLOR_PRIMARY for item in top][::-1]
    ax.barh(labels, scores, color=colors, alpha=0.85)
    for index, score in enumerate(scores):
        ax.text(score + 0.005, index, f"{score:.3f}", va="center", fontsize=8)
    ax.set_xlim(0, max(scores) * 1.18 + 0.02)
    ax.set_xlabel("Composite score (0.4 significance + 0.3 effect + 0.2 biology + 0.1 literature)")
    ax.set_title(f"Top {len(top)} candidate splicing events")
    return _save(
        fig,
        output_dir,
        "candidate_ranking",
        "Candidate ranking",
        f"Composite ranking scores for the top {len(top)} candidate splicing events.",
    )


def plot_enrichment(
    results: Sequence[EnrichmentResult],
    output_dir: Path,
    top_n: int = 12,
) -> FigureResult:
    """Dot plot of enriched terms (fold enrichment vs FDR)."""
    fig, ax = plt.subplots(figsize=(7.0, 5.2))
    top = list(results)[:top_n]
    if not top:
        ax.text(0.5, 0.5, "No enriched terms", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, output_dir, "enrichment", "Functional enrichment", "placeholder")
    labels = [f"{item.term} [{item.ontology}]" for item in top][::-1]
    fold = [min(item.fold_enrichment, 50.0) for item in top][::-1]
    fdr = [max(item.fdr, 1e-6) for item in top][::-1]
    sizes = [max(30, item.gene_count * 45) for item in top][::-1]
    scatter = ax.scatter(fold, range(len(top)), s=sizes, c=-np.log10(fdr), cmap="Reds", alpha=0.9, edgecolors="#666666", linewidths=0.4)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Fold enrichment (capped at 50x)")
    ax.set_title("Enriched functional terms")
    ax.grid(axis="y", visible=False)
    bar = fig.colorbar(scatter, ax=ax, shrink=0.7)
    bar.set_label("-log10(FDR)")
    return _save(
        fig,
        output_dir,
        "enrichment",
        "Functional enrichment",
        "Enriched GO/KEGG terms among candidate genes; dot size = overlapping gene count.",
    )


#: (name, builder) pairs used by :func:`generate_all_figures`.
FIGURE_SPECS: dict[str, str] = {
    "volcano": "delta PSI vs significance",
    "event_type_counts": "event composition",
    "psi_heatmap": "per-sample PSI heatmap",
    "psi_distribution": "PSI distribution by group",
    "candidate_ranking": "candidate composite scores",
    "enrichment": "functional enrichment",
}


def generate_all_figures(
    events: Sequence[StandardEvent],
    samples: Sequence[SampleMetadata],
    candidates: Sequence[RankedCandidate],
    enrichment: Sequence[EnrichmentResult],
    output_dir: str | Path,
    *,
    fdr_threshold: float = 0.05,
    delta_psi_threshold: float = 0.1,
) -> list[FigureResult]:
    """Generate the full figure set into ``output_dir`` and return results."""
    directory = Path(output_dir)
    figures = [
        plot_volcano(events, directory, fdr_threshold, delta_psi_threshold),
        plot_event_type_counts(events, directory),
        plot_psi_heatmap(events, samples, directory),
        plot_psi_distribution(events, samples, directory),
        plot_candidate_ranking(candidates, directory),
        plot_enrichment(enrichment, directory),
    ]
    return figures
