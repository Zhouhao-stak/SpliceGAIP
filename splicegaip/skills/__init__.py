"""Splicing-specific skills for SpliceGAIP.

Skills are high-level analysis capabilities that combine:
- MCP tool calls (external databases, literature search)
- Local analysis (delta PSI computation, event classification)
- AI interpretation (clinical significance, functional impact)

Each skill is a self-contained unit that can be invoked from the UI
or programmatically from the agent team.
"""

from splicegaip.skills.gene_annotation import GeneAnnotationSkill
from splicegaip.skills.literature_search import LiteratureSearchSkill
from splicegaip.skills.pathway_enrichment import PathwayEnrichmentSkill
from splicegaip.skills.splice_interpretation import SpliceInterpretationSkill

__all__ = [
    "GeneAnnotationSkill",
    "LiteratureSearchSkill",
    "PathwayEnrichmentSkill",
    "SpliceInterpretationSkill",
]
