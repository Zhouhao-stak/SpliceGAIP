"""Knowledge tools available to the Interpreter agent."""

from __future__ import annotations

from splicegaip.tools.context import RunContext


def collect_literature_evidence(
    context: RunContext,
    genes: list[str] | None = None,
    max_per_gene: int = 2,
) -> str:
    """Collect literature evidence for candidate genes.

    Sources: the bundled curated knowledge base (always), PubMed via
    pymed (when the network is available) and the persistent ChromaDB
    literature store. Every record is traceable to its source.
    """
    target = genes if genes is not None else context.top_genes()
    if not target:
        message = "No candidate genes available; literature collection skipped."
        context.log("bio_interpreter", "collect_literature_evidence", "skipped", message)
        return message
    evidence = context.knowledge.collect_evidence(target, max_per_gene=max_per_gene)
    context.evidence = evidence
    covered = [gene for gene, entries in evidence.items() if entries]
    lines = [f"Collected evidence for {len(covered)}/{len(target)} candidate genes."]
    for gene in covered[:8]:
        entries = evidence[gene]
        first = entries[0].text.split(". ")[0]
        lines.append(f"- {gene}: {len(entries)} record(s); e.g. {first[:160]}")
    if len(covered) < len(target):
        missing = [gene for gene in target if gene not in covered]
        lines.append(f"No evidence found for: {', '.join(missing[:10])}")
    lines.append("Sources: " + "; ".join(context.knowledge.describe_sources()))
    message = "\n".join(lines)
    context.log("bio_interpreter", "collect_literature_evidence", "ok", message)
    return message


def interpret_candidates(context: RunContext) -> str:
    """Produce the structured biological interpretation of top candidates.

    Deterministic, evidence-grounded narrative assembled from computed
    statistics plus the collected literature records. In LLM mode the
    Interpreter agent composes the final prose itself; this function
    remains the offline fallback and the report's factual backbone.
    """
    from splicegaip.report.generator import build_interpretation

    interpretation = build_interpretation(context)
    context.memory.save_interpretation(context.project_id, "bio_interpreter", interpretation)
    context.log("bio_interpreter", "interpret_candidates", "ok", interpretation[:400])
    return interpretation
