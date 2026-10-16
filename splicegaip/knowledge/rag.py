"""RAG knowledge service.

Combines three evidence sources, all traceable:

1. the bundled curated knowledge base (always available, offline);
2. PubMed retrieval via pymed (when the network is available);
3. a persistent SQLite literature store of retrieved articles
   (NFS-safe; the earlier chromadb store hung on network filesystems
   because its Rust bindings cannot lock NFS files).

When neither the network nor the store is available the service still
answers from the bundled knowledge base, so the Interpreter agent is
never blocked.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from splicegaip.knowledge.base import KnowledgeRecord, lookup_genes
from splicegaip.knowledge.pubmed import PubMedArticle, PubMedRetriever

STORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS literature (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gene TEXT NOT NULL,
    pmid TEXT,
    title TEXT,
    abstract TEXT,
    journal TEXT,
    year TEXT,
    source TEXT,
    retrieved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_literature_gene ON literature(gene);
"""


@dataclass
class Evidence:
    """One piece of literature evidence."""

    gene: str
    text: str
    source: str
    pmid: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"gene": self.gene, "text": self.text, "source": self.source, "pmid": self.pmid}


class _LiteratureStore:
    """SQLite-backed persistent literature store (thread-safe)."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as connection:
            connection.executescript(STORE_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def add(self, gene: str, article: PubMedArticle) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO literature (gene, pmid, title, abstract, journal, year, source, retrieved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    gene,
                    article.pmid,
                    article.title,
                    article.abstract,
                    article.journal,
                    article.year,
                    "PubMed (live)",
                ),
            )

    def get(self, gene: str, limit: int = 3) -> list[Evidence]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM literature WHERE gene = ? ORDER BY id DESC LIMIT ?",
                (gene, limit),
            ).fetchall()
        return [
            Evidence(
                gene=gene,
                text=(f"{row['title']}\n{row['abstract']}").strip()[:600],
                source=str(row["source"]),
                pmid=str(row["pmid"] or ""),
            )
            for row in rows
        ]

    def count(self) -> int:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM literature").fetchone()
        return int(row["n"]) if row else 0


@dataclass
class KnowledgeService:
    """Literature evidence lookup for candidate genes."""

    store_path: Path | None = None
    enable_pubmed: bool = True
    _retriever: PubMedRetriever = field(default_factory=PubMedRetriever, repr=False)
    _store: _LiteratureStore | None = field(default=None, repr=False)

    # -- store -------------------------------------------------------------
    def _get_store(self) -> _LiteratureStore | None:
        if self._store is not None:
            return self._store
        if self.store_path is None:
            return None
        try:
            self._store = _LiteratureStore(self.store_path)
        except Exception:
            self._store = None
        return self._store

    # -- public API ----------------------------------------------------------
    def collect_evidence(
        self,
        genes: list[str],
        *,
        use_pubmed: bool | None = None,
        max_per_gene: int = 2,
    ) -> dict[str, list[Evidence]]:
        """Collect evidence for the given genes from all available sources."""
        genes = [gene for gene in dict.fromkeys(genes) if gene]
        evidence: dict[str, list[Evidence]] = {}

        for record in lookup_genes(genes):
            evidence.setdefault(record.gene, []).append(
                Evidence(
                    gene=record.gene,
                    text=record.summary(),
                    source=record.source,
                    pmid=";".join(record.pmids),
                )
            )

        if use_pubmed is None:
            use_pubmed = self.enable_pubmed
        if use_pubmed:
            articles_by_gene = self._retriever.search_for_genes(genes, max_per_gene=max_per_gene)
            store = self._get_store()
            for gene, articles in articles_by_gene.items():
                for article in articles:
                    if store is not None:
                        try:
                            store.add(gene, article)
                        except Exception:
                            pass
                    evidence.setdefault(gene, []).append(
                        Evidence(
                            gene=gene,
                            text=article.summary(),
                            source="PubMed (live)",
                            pmid=article.pmid,
                        )
                    )

        store = self._get_store()
        if store is not None:
            for gene in genes:
                try:
                    entries = store.get(gene, limit=2)
                except Exception:
                    entries = []
                if entries:
                    evidence.setdefault(gene, []).extend(entries)
        return evidence

    def literature_score(self, evidence: dict[str, list[Evidence]]) -> dict[str, int]:
        """Number of evidence records per gene (for candidate ranking)."""
        return {gene: len(entries) for gene, entries in evidence.items() if entries}

    def describe_sources(self) -> list[str]:
        """Human-readable list of active evidence sources."""
        sources = ["SpliceGAIP curated knowledge base (offline)"]
        if self.enable_pubmed and self._retriever.available:
            sources.append("PubMed via pymed (network)")
        store = self._get_store()
        if store is not None:
            try:
                sources.append(f"SQLite literature store ({store.count()} records)")
            except Exception:
                sources.append("SQLite literature store")
        return sources

    def export(self, path: str | Path) -> None:
        """Dump the evidence-source manifest to a JSON file (auditability)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"sources": self.describe_sources()}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
