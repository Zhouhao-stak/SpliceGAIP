"""Analysis pipeline: the single entry point used by CLI, API and UI.

Flow: load dataset -> validate -> create project -> build run context ->
run the multi-agent team -> persist results.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from splicegaip.config import (
    Settings,
    ensure_runtime_dirs,
    load_prepared_settings,
    load_settings,
    pubmed_enabled,
)
from splicegaip.agent.loop import AgentRunResult, run_autonomous
from splicegaip.agent.session import (
    build_followup_actions,
    load_state,
    parse_followup,
)
from splicegaip.data.loader import load_dataset
from splicegaip.integrations import capability_report
from splicegaip.data.validator import validate_dataset
from splicegaip.knowledge.rag import KnowledgeService
from splicegaip.memory.project_memory import ProjectMemory
from splicegaip.team import TeamRunResult, run_team
from splicegaip.tools.context import RunContext


@dataclass
class AnalysisOutcome:
    """Everything produced by one analysis run."""

    project_id: str
    query: str
    output_dir: Path
    dataset_summary: dict[str, Any]
    validation: dict[str, Any]
    team: TeamRunResult
    context: RunContext
    report_paths: dict[str, Path] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        """JSON payload for the API and the web UI.

        Everything the engine computed is exposed here so a client can render
        the full analysis without touching the filesystem: dataset overview,
        validation, ranked candidates with their four score components,
        enrichment results, literature evidence, interpretation, limitations,
        references and the agent workflow log.
        """
        from splicegaip.report.generator import ReportGenerator, build_interpretation

        generator = ReportGenerator(self.context)
        analysis = self.context.settings.analysis
        return {
            "project_id": self.project_id,
            "query": self.query,
            "output_dir": str(self.output_dir),
            "dataset": self.dataset_summary,
            "validation": self.validation,
            "mode": self.team.mode,
            "stopped_reason": self.team.stopped_reason,
            "tool_calls": len(self.team.tool_calls),
            "elapsed_seconds": round(self.team.elapsed_seconds, 2),
            "report_paths": {kind: str(path) for kind, path in self.report_paths.items()},
            # figure names (stable contract) + display metadata for the UI
            "figures": [figure.name for figure in self.context.figures],
            "figure_details": [
                {"name": figure.name, "title": figure.title, "caption": figure.caption}
                for figure in self.context.figures
            ],
            "top_candidates": [item.as_dict() for item in self.context.candidates[:20]],
            "enriched_terms": [item.term for item in self.context.enrichment[:10]],
            "enrichment": [
                {
                    "ontology": item.ontology,
                    "term": item.term,
                    "gene_count": item.gene_count,
                    "background_count": item.background_count,
                    "fold_enrichment": round(item.fold_enrichment, 3),
                    "p_value": item.p_value,
                    "fdr": item.fdr,
                    "genes": list(item.genes),
                }
                for item in self.context.enrichment[:20]
            ],
            "evidence": {
                gene: [entry.as_dict() for entry in entries]
                for gene, entries in self.context.evidence.items()
                if entries
            },
            "interpretation": build_interpretation(self.context),
            "limitations": generator._limitations(),  # noqa: SLF001 - same module family
            "references": generator._references(),
            "workflow": list(self.context.workflow_log),
            "plan": self.context.plan,
            "counts": {
                "events": len(self.context.dataset.events),
                "significant": len(self.context.significant_events),
                "candidates": len(self.context.candidates),
                "enrichment": len(self.context.enrichment),
                "figures": len(self.context.figures),
                "samples": len(self.context.dataset.samples),
                "annotated_genes": len(self.context.dataset.annotation),
            },
            "thresholds": {
                "fdr": analysis.fdr_threshold,
                "delta_psi": analysis.delta_psi_threshold,
                "min_support_reads": analysis.min_support_reads,
                "min_valid_samples": analysis.min_valid_samples,
                "top_candidates": analysis.top_candidates,
                "enrichment_alpha": analysis.enrichment_alpha,
            },
            # model enrichment (empty structures when no endpoint is set)
            "llm": self._llm_block(),
            # autonomous agent trace (empty when the legacy scripted mode ran)
            "agent": self._agent_block(),
            # Phase 2: statistical self-checks and external knowledge findings
            "hypotheses": [
                item.as_dict() for item in getattr(self.context, "hypotheses", None) or []
            ],
            "external_findings": {
                key: len(value) if hasattr(value, "__len__") else 1
                for key, value in (getattr(self.context, "external", None) or {}).items()
            },
            # which optional open-source backends are actually installed
            "capabilities": capability_report(),
        }

    def _llm_block(self) -> dict[str, Any]:
        """Everything the model added to this run (for the API and the UI)."""
        insights = getattr(self.context, "llm_insights", None) or {}
        if not isinstance(insights, dict):
            insights = {}
        understanding = getattr(self.context, "understanding", None) or insights.get("understanding") or {}
        status = insights.get("status") if isinstance(insights.get("status"), dict) else {}
        return {
            "enabled": bool(insights.get("enabled")),
            "model": str(insights.get("model") or ""),
            "language": str(insights.get("language") or ""),
            "features": list(insights.get("features") or []),
            "available_features": list(insights.get("available_features") or []),
            "base_url": str(status.get("base_url") or ""),
            "calls": int(insights.get("calls") or status.get("call_count") or 0),
            "errors": list(insights.get("errors") or [])[:5],
            "note": str(insights.get("note") or ""),
            "understanding": understanding if isinstance(understanding, dict) else {},
            "narrative": insights.get("narrative") or {},
            "gene_notes": insights.get("gene_notes") or {},
            "evidence_summaries": insights.get("evidence_summaries") or {},
            "hypotheses": insights.get("hypotheses") or {},
            "critique": insights.get("critique") or {},
        }


    def _agent_block(self) -> dict[str, Any]:
        """The autonomous agent's decision trace (empty in scripted mode)."""
        team = self.team
        if not isinstance(team, AgentRunResult):
            return {}
        return team.as_dict()


def run_analysis(
    query: str,
    input_path: str | Path,
    *,
    settings: Settings | None = None,
    project_id: str | None = None,
    output_root: str | Path | None = None,
    confirm_handler: Any | None = None,
) -> AnalysisOutcome:
    """Run the full analysis pipeline for one query against one input dataset."""
    if settings is None:
        settings, storage_warnings = load_prepared_settings()
        for warning in storage_warnings:
            print(f"[splicegaip] warning: {warning}")
    ensure_runtime_dirs(settings)

    dataset = load_dataset(input_path)
    validation = validate_dataset(dataset)
    if not validation.ok:
        errors = "; ".join(issue.message for issue in validation.errors)
        raise ValueError(f"Input dataset failed validation: {errors}")

    project_id = project_id or f"SPN-{uuid.uuid4().hex[:8].upper()}"
    output_root_path = Path(output_root) if output_root else settings.paths.runtime_root / "projects"
    output_dir = output_root_path / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    memory = ProjectMemory(settings.paths.memory_db)
    memory.create_project(
        project_id=project_id,
        name=dataset.name,
        query=query,
        source_dir=str(dataset.source_dir),
        source_format=dataset.source_format,
    )
    memory.save_samples(project_id, dataset.samples)

    knowledge = KnowledgeService(
        store_path=settings.paths.literature_db,
        enable_pubmed=pubmed_enabled(),
    )
    context = RunContext(
        project_id=project_id,
        query=query,
        dataset=dataset,
        settings=settings,
        memory=memory,
        knowledge=knowledge,
        output_dir=output_dir,
        validation=validation,
    )
    context.log("system", "run_started", "ok", f"query={query!r} input={dataset.source_dir}")

    # Pre-analysis intent understanding (model-based when configured).
    if settings.llm.usable:
        try:
            from splicegaip.llm.tasks import understand_query

            context.understanding = understand_query(query, settings=settings)
            context.log(
                "llm",
                "understand_query",
                "ok",
                f"type={context.understanding.get('analysis_type')} "
                f"source={context.understanding.get('source')}",
            )
        except Exception as error:  # noqa: BLE001 - never block the run
            context.log("llm", "understand_query", "warning", str(error)[:300])

    if settings.agent.agentic:
        from splicegaip.agent.loop import run_autonomous

        team_result = run_autonomous(context, confirm_handler=confirm_handler)
    else:
        team_result = run_team(context)

    # Model enrichment: narrative, gene notes, evidence summaries,
    # hypotheses, critique, limitations. No-op without an endpoint.
    try:
        from splicegaip.llm.tasks import enrich_context

        enrich_context(context)
    except Exception as error:  # noqa: BLE001 - enrichment is optional
        print(f"[splicegaip] warning: LLM enrichment skipped ({error})")
        context.log("llm", "enrich_context", "warning", str(error)[:300])

    # (Re)generate the report so it always matches the final context:
    # deterministic when no model is configured, AI-enriched when it is.
    from splicegaip.report.generator import ReportGenerator

    generator = ReportGenerator(context)
    context.report_paths = generator.generate(str(output_dir), formats=settings.report_formats)
    for kind, path in context.report_paths.items():
        memory.save_artifact(project_id, f"report:{kind}", str(path))

    context.log("system", "run_finished", "ok", f"mode={team_result.mode} reason={team_result.stopped_reason}")
    return AnalysisOutcome(
        project_id=project_id,
        query=query,
        output_dir=output_dir,
        dataset_summary=dataset.summary(),
        validation=validation.as_dict(),
        team=team_result,
        context=context,
        report_paths=context.report_paths,
    )


def resume_analysis(
    project_id: str,
    query: str,
    *,
    settings: Settings | None = None,
    output_root: str | Path | None = None,
    confirm_handler: Any | None = None,
) -> AnalysisOutcome:
    """Continue a prior project with a follow-up query (multi-turn analysis).

    Unlike :func:`run_analysis`, this reloads the previous decision state and
    only executes the new intent (gene focus or event-type restriction), then
    lets the normal loop re-satisfy the tail criteria. The dataset is
    re-loaded (deterministic) so the heavy observation/filtering is skipped.
    """
    if settings is None:
        settings, storage_warnings = load_prepared_settings()
        for warning in storage_warnings:
            print(f"[splicegaip] warning: {warning}")
    ensure_runtime_dirs(settings)

    memory = ProjectMemory(settings.paths.memory_db)
    project = memory.get_project(project_id)
    if project is None:
        raise ValueError(f"Unknown project id: {project_id}")
    source_dir = project.get("source_dir")
    if not source_dir:
        raise ValueError(f"Project {project_id} has no recorded source directory.")

    output_root_path = Path(output_root) if output_root else settings.paths.runtime_root / "projects"
    output_dir = output_root_path / project_id
    if not output_dir.is_dir():
        raise ValueError(f"Project artifacts missing for {project_id} at {output_dir}.")

    dataset = load_dataset(source_dir)
    validation = validate_dataset(dataset)
    if not validation.ok:
        errors = "; ".join(issue.message for issue in validation.errors)
        raise ValueError(f"Input dataset failed validation: {errors}")

    knowledge = KnowledgeService(
        store_path=settings.paths.literature_db,
        enable_pubmed=pubmed_enabled(),
    )
    context = RunContext(
        project_id=project_id,
        query=query,
        dataset=dataset,
        settings=settings,
        memory=memory,
        knowledge=knowledge,
        output_dir=output_dir,
        validation=validation,
    )
    context.log("system", "resume_started", "ok", f"query={query!r} input={dataset.source_dir}")

    prior_state = load_state(output_dir, context)
    if prior_state is None:
        raise ValueError(f"No saved agent state for {project_id}; cannot resume.")

    # Restore the derived context that a fresh dataset load does not carry:
    # re-filter/rank with the prior thresholds (deterministic) and recover the
    # on-disk figures + report so the loop does not re-run the whole pipeline.
    prior_params = prior_state.params
    try:
        from splicegaip.tools.analysis_tools import (
            filter_significant_events as _filter_events,
            rank_candidates as _rank_candidates,
        )

        _filter_events(context, prior_params.get("fdr"), prior_params.get("delta_psi"))
        _rank_candidates(context, prior_params.get("top_n"))
    except Exception as error:  # noqa: BLE001 - derived state is best-effort
        context.log("agent", "resume_restore", "warning", str(error)[:200])

    figures_dir = output_dir / "figures"
    if figures_dir.is_dir():
        from splicegaip.analysis.visualization import FigureResult

        context.figures = [
            FigureResult(
                name=png.stem,
                title=png.stem,
                png_path=png,
                svg_path=png,
                caption="restored from previous run",
            )
            for png in sorted(figures_dir.glob("*.png"))
        ]
    for kind in ("html", "pdf"):
        report_path = output_dir / f"report.{kind}"
        if report_path.exists():
            context.report_paths[kind] = str(report_path)

    known_genes = [
        (item.gene_symbol or item.gene_id) for item in context.dataset.events
    ]
    intent = parse_followup(query, known_genes=known_genes)
    followup = build_followup_actions(intent, top_n=settings.analysis.top_candidates)
    if not followup:
        raise ValueError(
            "Follow-up query did not match any known gene or event type; "
            f"known event types are {('SE','MXE','RI','A3SS','A5SS')}."
        )
    context.log(
        "agent",
        "followup_intent",
        "ok",
        f"genes={intent['genes']} event_types={intent['event_types']}",
    )

    team_result = run_autonomous(
        context,
        settings,
        confirm_handler=confirm_handler,
        state=prior_state,
        followup=followup,
    )

    try:
        from splicegaip.llm.tasks import enrich_context

        enrich_context(context)
    except Exception as error:  # noqa: BLE001 - enrichment is optional
        context.log("llm", "enrich_context", "warning", str(error)[:300])

    from splicegaip.report.generator import ReportGenerator

    generator = ReportGenerator(context)
    context.report_paths = generator.generate(str(output_dir), formats=settings.report_formats)
    for kind, path in context.report_paths.items():
        memory.save_artifact(project_id, f"report:{kind}", str(path))

    context.log(
        "system",
        "resume_finished",
        "ok",
        f"mode={team_result.mode} reason={team_result.stopped_reason} steps={len(team_result.steps)}",
    )
    return AnalysisOutcome(
        project_id=project_id,
        query=query,
        output_dir=output_dir,
        dataset_summary=dataset.summary(),
        validation=validation.as_dict(),
        team=team_result,
        context=context,
        report_paths=context.report_paths,
    )


def project_status(project_id: str, settings: Settings | None = None) -> dict[str, Any] | None:
    """Load a persisted project's status from the analysis memory."""
    if settings is None:
        settings, _ = load_prepared_settings()
    memory = ProjectMemory(settings.paths.memory_db)
    project = memory.get_project(project_id)
    if project is None:
        return None
    return {
        "project": project,
        "samples": memory.load_samples(project_id) if hasattr(memory, "load_samples") else [],
        "events": len(memory.load_events(project_id)),
        "candidates": memory.load_candidates(project_id)[:10],
        "enrichment": memory.load_enrichment(project_id)[:10],
        "artifacts": memory.load_artifacts(project_id),
        "plan": memory.load_plan(project_id),
        "logs": memory.load_logs(project_id),
    }


def list_projects(settings: Settings | None = None) -> list[dict[str, Any]]:
    """List known projects (most recent first)."""
    if settings is None:
        settings, _ = load_prepared_settings()
    memory = ProjectMemory(settings.paths.memory_db)
    return memory.list_projects()
