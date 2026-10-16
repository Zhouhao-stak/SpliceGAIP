"""Deterministic analysis policy.

Computes the full response script for the offline (no-LLM) mode:

* the Planner's plan JSON (rule-based goal classification);
* the Analyst's ordered tool calls with concrete arguments;
* the Interpreter's ordered tool calls;
* final summary texts, generated lazily from the run context after the
  tools have executed.

The script is replayed through the real AutoGen team by
:class:`splicegaip.llm.fallback.DeterministicClient`, so the multi-agent
machinery is exercised identically in both modes.
"""

from __future__ import annotations

from typing import Any

from splicegaip.llm.fallback import TERMINATION_TOKEN, DeterministicClient
from splicegaip.tools.context import RunContext

#: Keyword -> analysis type mapping for the planner policy.
_GOAL_KEYWORDS: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("剪接", "splic", "AS event", "alternative splicing", "psi", "exon"),
        "differential_AS",
        "Identify differential alternative splicing events between the experimental groups.",
    ),
    (
        ("表达", "differential expression", "deg", "deseq", "log2fc"),
        "DE_analysis",
        "Identify differentially expressed genes between the experimental groups.",
    ),
    (
        ("候选", "candidate", "rank", "priorit", "hub", "biomarker"),
        "differential_AS",
        "Prioritize candidate splicing events and genes for downstream validation.",
    ),
    (
        ("富集", "enrich", "pathway", "go ", "kegg", "功能"),
        "differential_AS",
        "Characterize the functional pathways of differentially spliced genes.",
    ),
]

_WORKFLOW: list[dict[str, Any]] = [
    {"step": 1, "agent": "bio_analyst", "action": "summarize_dataset"},
    {"step": 2, "agent": "bio_analyst", "action": "filter_significant_events"},
    {"step": 3, "agent": "bio_analyst", "action": "rank_candidates"},
    {"step": 4, "agent": "bio_analyst", "action": "run_enrichment"},
    {"step": 5, "agent": "bio_analyst", "action": "generate_figures"},
    {"step": 6, "agent": "bio_interpreter", "action": "collect_literature_evidence"},
    {"step": 7, "agent": "bio_interpreter", "action": "generate_report"},
]


def classify_query(query: str) -> tuple[str, str]:
    """Map the user query to (analysis_type, goal sentence)."""
    lowered = query.lower()
    for keywords, analysis_type, goal in _GOAL_KEYWORDS:
        if any(keyword.lower() in lowered for keyword in keywords):
            return analysis_type, goal
    return "exploration", (
        "Explore the alternative splicing landscape of the supplied dataset and summarize "
        "the most notable events."
    )


def build_plan(context: RunContext) -> dict[str, Any]:
    """Build the Planner's plan JSON from the query and dataset state."""
    analysis_type, goal = classify_query(context.query)
    dataset = context.dataset
    limitations: list[str] = []
    if not dataset.annotation:
        limitations.append("No gene annotation table supplied; functional enrichment will be skipped.")
    if context.validation is not None:
        limitations.extend(issue.message for issue in context.validation.warnings[:3])
    if not dataset.samples:
        limitations.append("No sample metadata; group-level summaries are unavailable.")
    return {
        "goal": goal,
        "analysis_type": analysis_type,
        "workflow": list(_WORKFLOW),
        "required_files": [str(dataset.source_dir)],
        "expected_outputs": [
            "filtered significant events",
            "ranked candidates",
            "figures",
            "HTML/PDF report",
        ],
        "potential_limitations": limitations or ["none identified"],
    }


def _planner_text(context: RunContext) -> str:
    import json

    return json.dumps(build_plan(context), indent=2)


def _analyst_script(context: RunContext) -> list[dict[str, Any]]:
    """Ordered analyst tool calls (arguments from platform configuration)."""
    analysis = context.settings.analysis
    return [
        {"tool": "summarize_dataset"},
        {
            "tool": "filter_significant_events",
            "args": {
                "fdr_threshold": analysis.fdr_threshold,
                "delta_psi_threshold": analysis.delta_psi_threshold,
            },
        },
        {"tool": "rank_candidates", "args": {"top_n": analysis.top_candidates}},
        {"tool": "run_enrichment", "args": {"alpha": analysis.enrichment_alpha}},
        {"tool": "generate_figures", "args": {"output_dir": str(context.output_dir / "figures")}},
    ]


def _interpreter_script(context: RunContext) -> list[dict[str, Any]]:
    return [
        {
            "tool": "collect_literature_evidence",
            "args": {"max_per_gene": 2},
        },
        {"tool": "interpret_candidates"},
        {"tool": "generate_report", "args": {"output_dir": str(context.output_dir)}},
    ]


def _analyst_final_text(context: RunContext) -> str:
    """Analyst summary, generated from the run context after tools executed."""
    from splicegaip.tools.analysis_tools import analysis_summary

    summary = analysis_summary(context)
    top = context.candidates[:5]
    listing = ", ".join(
        f"{item.gene_symbol or item.gene_id} ({item.event_type}, score={item.score:.3f})" for item in top
    )
    return (
        "Analysis complete.\n"
        f"- events analyzed: {summary['total_events']}\n"
        f"- significant events: {summary['significant_events']}\n"
        f"- candidates ranked: {summary['candidate_count']}\n"
        f"- enriched terms: {summary['enriched_terms']}\n"
        f"- figures generated: {summary['figures']}\n"
        f"- top candidates: {listing or 'none'}\n"
        "Handing over to the Interpreter agent for biological interpretation and reporting."
    )


def _interpreter_final_text(context: RunContext) -> str:
    """Interpreter summary, generated from the run context after tools executed."""
    from splicegaip.report.generator import build_interpretation

    interpretation = build_interpretation(context)
    reports = ", ".join(f"{kind}: {path}" for kind, path in context.report_paths.items())
    top_genes = context.top_genes(10)
    return (
        f"{interpretation}\n\n"
        f"Top candidate genes: {', '.join(top_genes) if top_genes else 'none'}.\n"
        f"Report written to {reports or 'the output directory'}.\n"
        f"{TERMINATION_TOKEN}"
    )


def build_deterministic_clients(
    context: RunContext,
) -> tuple[DeterministicClient, DeterministicClient, DeterministicClient]:
    """Build the three scripted agent clients (planner, analyst, interpreter)."""
    planner = DeterministicClient("bio_planner", script=[{"text": _planner_text(context)}])
    analyst = DeterministicClient("bio_analyst", script=_analyst_script(context))
    interpreter = DeterministicClient("bio_interpreter", script=_interpreter_script(context))
    analyst.set_finalizer(lambda: _analyst_final_text(context))
    interpreter.set_finalizer(lambda: _interpreter_final_text(context))
    return planner, analyst, interpreter


def speaker_order() -> list[str]:
    """Planned speaker order: planner once, analyst per tool + final, interpreter per tool + final."""
    analyst_turns = len(_WORKFLOW[:5]) + 1  # 5 tool calls + final summary
    interpreter_turns = len(_WORKFLOW[5:]) + 1  # 3 tool calls + final summary
    return (
        ["bio_planner"]
        + ["bio_analyst"] * analyst_turns
        + ["bio_interpreter"] * interpreter_turns
    )
