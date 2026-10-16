"""Shared run context for tools and agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from splicegaip.analysis.enrichment import EnrichmentResult
from splicegaip.analysis.visualization import FigureResult
from splicegaip.config import Settings
from splicegaip.data.loader import Dataset
from splicegaip.knowledge.rag import Evidence, KnowledgeService
from splicegaip.memory.project_memory import ProjectMemory
from splicegaip.splicing.filtering import FilterReport
from splicegaip.splicing.ranking import RankedCandidate
from splicegaip.splicing.schema import StandardEvent


@dataclass
class RunContext:
    """Everything the agents and tools share during one analysis run."""

    project_id: str
    query: str
    dataset: Dataset
    settings: Settings
    memory: ProjectMemory
    knowledge: KnowledgeService
    output_dir: Path
    plan: dict[str, Any] = field(default_factory=dict)
    validation: Any = None
    filter_report: FilterReport | None = None
    significant_events: list[StandardEvent] = field(default_factory=list)
    candidates: list[RankedCandidate] = field(default_factory=list)
    enrichment: list[EnrichmentResult] = field(default_factory=list)
    figures: list[FigureResult] = field(default_factory=list)
    evidence: dict[str, list[Evidence]] = field(default_factory=dict)
    report_paths: dict[str, Path] = field(default_factory=dict)
    workflow_log: list[dict[str, str]] = field(default_factory=list)
    #: Model-enriched insights (narrative, gene notes, evidence summaries,
    #: hypotheses, critique). Empty in deterministic mode.
    llm_insights: dict[str, Any] = field(default_factory=dict)
    #: Structured intent produced before the analysis (rule-based or model-based).
    understanding: dict[str, Any] = field(default_factory=dict)
    #: Findings retrieved from external knowledge sources (skills). Keyed by
    #: capability: ``gene_annotation`` / ``literature`` / ``pathways`` /
    #: ``interpretation``. Empty when the skills are disabled or unreachable.
    external: dict[str, Any] = field(default_factory=dict)
    #: Pre-registered hypothesis tests the agent ran on its own result.
    hypotheses: list[Any] = field(default_factory=list)

    def log(self, agent: str, action: str, status: str = "ok", detail: str = "") -> None:
        entry = {"agent": agent, "action": action, "status": status, "detail": detail}
        self.workflow_log.append(entry)
        self.memory.log(self.project_id, agent, action, status, detail)

    def top_genes(self, limit: int | None = None) -> list[str]:
        from splicegaip.splicing.ranking import top_candidate_genes

        return top_candidate_genes(self.candidates, limit or self.settings.analysis.top_candidates)
