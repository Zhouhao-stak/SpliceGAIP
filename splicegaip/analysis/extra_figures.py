"""On-demand publication-grade figures derived from persisted project state.

These complement :mod:`splicegaip.analysis.visualization`: they only need the
ranked candidates / sample metadata stored in the project memory, so they can
be generated lazily for any existing project (including projects analysed
before this module existed).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, Rectangle

COLOR_UP = "#D55E00"
COLOR_DOWN = "#0072B2"
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


def _save(fig: Figure, output_dir: Path, name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    png = output_dir / f"{name}.png"
    svg = output_dir / f"{name}.svg"
    fig.savefig(png, format="png", bbox_inches="tight", facecolor="white")
    fig.savefig(svg, format="svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png


def _placeholder(fig: Figure, ax, message: str, output_dir: Path, name: str) -> Path:
    ax.text(0.5, 0.5, message, ha="center", va="center", color=COLOR_NEUTRAL)
    ax.set_axis_off()
    return _save(fig, output_dir, name)


def _label(candidate: dict[str, Any]) -> str:
    gene = candidate.get("gene_symbol") or candidate.get("gene_id") or "?"
    return f"{gene} ({candidate.get('event_type', '?')})"


def plot_dpsi_waterfall(candidates: Sequence[dict[str, Any]], output_dir: Path, top_n: int = 25) -> Path:
    """Waterfall plot of the largest |delta PSI| candidates."""
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    ranked = sorted(
        (c for c in candidates if c.get("delta_psi") is not None),
        key=lambda c: abs(c["delta_psi"]),
        reverse=True,
    )[:top_n]
    if not ranked:
        return _placeholder(fig, ax, "No delta PSI values available", output_dir, "dpsi_waterfall")
    ranked = ranked[::-1]
    labels = [_label(c) for c in ranked]
    values = [c["delta_psi"] for c in ranked]
    colors = [COLOR_UP if v > 0 else COLOR_DOWN for v in values]
    ypos = np.arange(len(values))
    ax.barh(ypos, values, color=colors, alpha=0.85, height=0.72)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.axvline(0, color="#333333", lw=0.8)
    for threshold in (0.1, -0.1):
        ax.axvline(threshold, color=COLOR_NEUTRAL, lw=0.8, ls=":")
    ax.set_xlabel("delta PSI (group2 - group1)")
    ax.set_title(f"Waterfall of top {len(values)} differential splicing events by |delta PSI|")
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, color=COLOR_UP, alpha=0.85, label="increased inclusion"),
            plt.Rectangle((0, 0), 1, 1, color=COLOR_DOWN, alpha=0.85, label="decreased inclusion"),
        ],
        frameon=False,
        loc="lower right",
        fontsize=8,
    )
    return _save(fig, output_dir, "dpsi_waterfall")


def plot_dpsi_ecdf(candidates: Sequence[dict[str, Any]], output_dir: Path) -> Path:
    """Empirical CDF of delta PSI with effect-size thresholds annotated."""
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    values = np.array([c["delta_psi"] for c in candidates if c.get("delta_psi") is not None])
    if values.size == 0:
        return _placeholder(fig, ax, "No delta PSI values available", output_dir, "dpsi_ecdf")
    ordered = np.sort(values)
    ecdf = np.arange(1, ordered.size + 1) / ordered.size
    ax.step(ordered, ecdf, where="post", color=COLOR_DOWN, lw=1.6, label="ECDF of delta PSI")
    ax.axvline(0, color="#333333", lw=0.8)
    for threshold, text in ((0.1, "|dPSI|>0.1"), (-0.1, "")):
        ax.axvline(threshold, color=COLOR_UP, lw=0.9, ls="--")
        if text:
            ax.text(threshold, 0.05, text, rotation=90, va="bottom", ha="right", fontsize=8, color=COLOR_UP)
    frac_large = float(np.mean(np.abs(values) > 0.1))
    ax.set_xlabel("delta PSI")
    ax.set_ylabel("Empirical cumulative probability")
    ax.set_title(f"Delta PSI distribution (n={values.size}; {frac_large:.0%} with |dPSI|>0.1)")
    ax.legend(frameon=False, fontsize=8)
    return _save(fig, output_dir, "dpsi_ecdf")


def plot_fdr_scree(candidates: Sequence[dict[str, Any]], output_dir: Path) -> Path:
    """Rank vs -log10(FDR) scree plot highlighting the significance elbow."""
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    fdrs = sorted(
        (max(c["fdr"], 1e-300) for c in candidates if c.get("fdr") is not None),
    )
    if not fdrs:
        return _placeholder(fig, ax, "No FDR values available", output_dir, "fdr_scree")
    neg_log = -np.log10(np.array(fdrs))
    ax.plot(np.arange(1, len(neg_log) + 1), neg_log, marker="o", ms=4, lw=1.2, color=COLOR_DOWN)
    ax.axhline(-np.log10(0.05), color=COLOR_UP, lw=1.0, ls="--")
    ax.text(1, -np.log10(0.05), " FDR=0.05", va="bottom", fontsize=8, color=COLOR_UP)
    significant = int(np.sum(neg_log > -np.log10(0.05)))
    ax.set_xlabel("Candidate rank (most significant first)")
    ax.set_ylabel("-log10(FDR)")
    ax.set_title(f"Significance scree plot ({significant} candidates below FDR 0.05)")
    return _save(fig, output_dir, "fdr_scree")


def plot_event_significance(
    candidates: Sequence[dict[str, Any]],
    output_dir: Path,
    fdr_threshold: float = 0.05,
    delta_psi_threshold: float = 0.1,
) -> Path:
    """Stacked bars: significant vs non-significant events per event type."""
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    buckets: dict[str, list[int]] = {}
    for candidate in candidates:
        etype = candidate.get("event_type") or "?"
        sig = (
            candidate.get("fdr") is not None
            and candidate.get("delta_psi") is not None
            and candidate["fdr"] < fdr_threshold
            and abs(candidate["delta_psi"]) > delta_psi_threshold
        )
        slot = buckets.setdefault(etype, [0, 0])
        slot[0 if sig else 1] += 1
    if not buckets:
        return _placeholder(fig, ax, "No candidates", output_dir, "event_significance")
    labels = sorted(buckets)
    sig_counts = [buckets[label][0] for label in labels]
    ns_counts = [buckets[label][1] for label in labels]
    xpos = np.arange(len(labels))
    ax.bar(xpos, sig_counts, color=COLOR_UP, alpha=0.85, label=f"significant (FDR<{fdr_threshold}, |dPSI|>{delta_psi_threshold})")
    ax.bar(xpos, ns_counts, bottom=sig_counts, color=COLOR_NEUTRAL, alpha=0.6, label="not significant")
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Candidate count")
    ax.set_title("Significance composition per splicing event type")
    ax.legend(frameon=False, fontsize=8)
    return _save(fig, output_dir, "event_significance")


def plot_score_components(candidates: Sequence[dict[str, Any]], output_dir: Path, top_n: int = 10) -> Path:
    """Stacked bar of the ranking-score components for top candidates."""
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    top = list(candidates)[:top_n]
    rows = []
    for candidate in top:
        components = candidate.get("components_json")
        if isinstance(components, str):
            try:
                components = json.loads(components)
            except Exception:  # noqa: BLE001 - tolerate malformed payloads
                components = None
        if not isinstance(components, dict):
            continue
        rows.append((candidate, components))
    if not rows:
        return _placeholder(fig, ax, "No score components available", output_dir, "score_components")
    labels = [_label(c) for c, _ in rows][::-1]
    keys = ["significance", "effect", "biology", "literature"]
    colors = [COLOR_DOWN, COLOR_UP, "#009E73", COLOR_HIGHLIGHT]
    left = np.zeros(len(rows))
    ypos = np.arange(len(rows))
    for key, color in zip(keys, colors):
        weights = np.array([0.0] * len(rows))
        for index, (_candidate, components) in enumerate(rows):
            weights[index] = float(components.get(key, 0.0) or 0.0)
        values = weights[::-1]
        ax.barh(ypos, values, left=left, color=color, alpha=0.85, label=key)
        left = left + values
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Weighted score contribution")
    ax.set_title(f"Ranking score decomposition (top {len(rows)} candidates)")
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    return _save(fig, output_dir, "score_components")


def plot_sample_composition(samples: Sequence[dict[str, Any]], output_dir: Path) -> Path:
    """Group / batch composition of the analysed cohort."""
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4))
    groups: dict[str, int] = {}
    batches: dict[str, int] = {}
    for sample in samples:
        group = sample.get("group_name") or sample.get("condition") or "unknown"
        batch = sample.get("batch") or "unknown"
        groups[group] = groups.get(group, 0) + 1
        batches[batch] = batches.get(batch, 0) + 1
    if not groups:
        return _placeholder(fig, axes[0], "No sample metadata", output_dir, "sample_composition")
    ax = axes[0]
    palette = [COLOR_DOWN, COLOR_UP, "#009E73", COLOR_HIGHLIGHT, "#F0E442"]
    wedges, _labels, autotexts = ax.pie(
        groups.values(),
        labels=groups.keys(),
        autopct=lambda p: f"{p:.0f}%\n(n={int(round(p * sum(groups.values()) / 100))})",
        colors=[palette[i % len(palette)] for i in range(len(groups))],
        startangle=90,
        textprops={"fontsize": 9},
    )
    for text in autotexts:
        text.set_color("white")
        text.set_fontsize(8)
    ax.set_title(f"Cohort composition (n={sum(groups.values())})")
    ax = axes[1]
    blabels = sorted(batches)
    bvalues = [batches[label] for label in blabels]
    ax.bar(blabels, bvalues, color=COLOR_DOWN, alpha=0.8)
    for index, value in enumerate(bvalues):
        ax.text(index, value, str(value), ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("Batch")
    ax.set_ylabel("Samples")
    ax.set_title("Batch distribution")
    fig.tight_layout()
    return _save(fig, output_dir, "sample_composition")


def plot_event_schematic(output_dir: Path) -> Path:
    """Classic schematic of the five alternative splicing event classes."""
    fig, axes = plt.subplots(5, 1, figsize=(7.4, 8.6))
    constitutive = "#56B4E9"
    alternative = COLOR_UP
    intron_color = "#CCCCCC"

    def _exon(ax, x, width, color, height=0.34, y=0.4):
        ax.add_patch(Rectangle((x, y), width, height, facecolor=color, edgecolor="#333333", lw=0.8))

    def _line(ax, x0, x1, y=0.57):
        ax.plot([x0, x1], [y, y], color=intron_color, lw=1.4, zorder=0)

    panels = [
        ("SE - Skipped exon", "skip"),
        ("MXE - Mutually exclusive exons", "mxe"),
        ("A5SS - Alternative 5' splice site", "a5ss"),
        ("A3SS - Alternative 3' splice site", "a3ss"),
        ("RI - Retained intron", "ri"),
    ]
    for ax, (title, kind) in zip(axes, panels):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 1.2)
        ax.set_axis_off()
        ax.set_title(title, loc="left", fontsize=10, fontweight="bold")
        if kind == "skip":
            _line(ax, 0.4, 9.6)
            _exon(ax, 0.6, 1.6, constitutive)
            _exon(ax, 4.2, 1.6, alternative)
            _exon(ax, 7.8, 1.6, constitutive)
            ax.annotate("", xy=(4.2, 0.95), xytext=(2.2, 0.75), arrowprops=dict(arrowstyle="-", ls=":", color=COLOR_UP))
            ax.annotate("", xy=(7.8, 0.75), xytext=(5.8, 0.95), arrowprops=dict(arrowstyle="-", ls=":", color=COLOR_UP))
        elif kind == "mxe":
            _line(ax, 0.4, 9.6)
            _exon(ax, 0.6, 1.4, constitutive)
            _exon(ax, 3.4, 1.4, alternative)
            _exon(ax, 5.4, 1.4, alternative, y=0.02)
            _exon(ax, 8.0, 1.4, constitutive)
        elif kind == "a5ss":
            _line(ax, 0.4, 9.6)
            _exon(ax, 0.6, 1.6, constitutive)
            _exon(ax, 4.0, 2.2, alternative)
            _exon(ax, 4.6, 1.6, "white", height=0.34, y=0.4)
            ax.add_patch(Rectangle((4.0, 0.4), 0.6, 0.34, facecolor=alternative, edgecolor="#333333", lw=0.8, hatch="//"))
            _exon(ax, 7.8, 1.6, constitutive)
        elif kind == "a3ss":
            _line(ax, 0.4, 9.6)
            _exon(ax, 0.6, 1.6, constitutive)
            _exon(ax, 4.0, 2.2, alternative)
            ax.add_patch(Rectangle((5.6, 0.4), 0.6, 0.34, facecolor=alternative, edgecolor="#333333", lw=0.8, hatch="//"))
            _exon(ax, 7.8, 1.6, constitutive)
        else:  # ri
            _line(ax, 0.4, 9.6)
            _exon(ax, 0.6, 1.6, constitutive)
            ax.add_patch(Rectangle((3.6, 0.4), 2.6, 0.34, facecolor=intron_color, edgecolor="#333333", lw=0.8, hatch=".."))
            ax.text(4.9, 0.57, "intron retained", ha="center", va="center", fontsize=8, color="#444444")
            _exon(ax, 7.8, 1.6, constitutive)
    fig.suptitle("Alternative splicing event classes detected by SpliceGAIP", y=0.995, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    return _save(fig, output_dir, "event_schematic")


#: Lazy figure builders keyed by endpoint figure name.
ON_DEMAND_FIGURES: dict[str, str] = {
    "dpsi_waterfall": "waterfall of top |delta PSI| candidates",
    "dpsi_ecdf": "empirical CDF of delta PSI",
    "fdr_scree": "significance scree plot",
    "event_significance": "significant vs non-significant per type",
    "score_components": "ranking score decomposition",
    "sample_composition": "cohort group / batch composition",
    "event_schematic": "schematic of AS event classes",
}
