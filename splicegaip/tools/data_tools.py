"""Data tools available to the Analyst agent."""

from __future__ import annotations

from splicegaip.tools.context import RunContext


def summarize_dataset(context: RunContext) -> str:
    """Return a compact summary of the loaded dataset.

    The dataset itself is loaded and validated by the orchestrator before
    the agent team starts; this tool exposes that state to the agents.
    """
    summary = context.dataset.summary()
    lines = [
        f"Dataset '{summary['name']}' (format: {summary['source_format']})",
        f"- AS events: {summary['event_count']}",
        f"- samples: {summary['sample_count']} across groups "
        + ", ".join(f"{group}={count}" for group, count in summary["groups"].items()),
        f"- event types: " + ", ".join(f"{key}={value}" for key, value in summary["event_types"].items()),
        f"- annotated genes: {summary['annotated_genes']}",
    ]
    if summary["de_gene_count"]:
        lines.append(f"- differential expression rows: {summary['de_gene_count']}")
    if context.validation is not None:
        result = context.validation
        lines.append(f"- validation: {len(result.errors)} error(s), {len(result.warnings)} warning(s)")
    context.log("bio_analyst", "summarize_dataset", "ok", f"{summary['event_count']} events")
    return "\n".join(lines)
