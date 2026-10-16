"""Knowledge subpackage: RAG literature evidence and PubMed retrieval."""

from splicegaip.knowledge.base import (
    BUNDLED_GENE_KNOWLEDGE,
    KnowledgeRecord,
    known_genes,
    lookup_genes,
)
from splicegaip.knowledge.pubmed import PubMedArticle, PubMedRetriever
from splicegaip.knowledge.rag import Evidence, KnowledgeService

__all__ = [
    "BUNDLED_GENE_KNOWLEDGE",
    "Evidence",
    "KnowledgeRecord",
    "KnowledgeService",
    "PubMedArticle",
    "PubMedRetriever",
    "known_genes",
    "lookup_genes",
]
