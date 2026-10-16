"""Lab-level knowledge persistence: remember recurrent genes across projects.

This module maintains a SQLite-backed knowledge base that tracks which genes
and pathways appear repeatedly in the user's analyses. The agent consults this
knowledge before interpreting candidates, allowing it to highlight genes that
have been significant in multiple prior projects.

The knowledge base is separate from the episodic memory (which stores
thresholds) and project memory (which stores per-project results). It focuses
on **cross-project recurrence patterns**.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class KnowledgeEntry:
    """A single record of a gene appearing in a project."""

    gene: str
    project_id: str
    event_type: str | None = None
    delta_psi: float | None = None
    fdr: float | None = None
    rank: int | None = None


class LabKnowledge:
    """Persistent cross-project knowledge base for recurrent genes/pathways."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Initialize the knowledge base.

        Parameters
        ----------
        db_path :
            Path to the SQLite database file. If None, uses
            ``runtime/lab_knowledge.sqlite3`` relative to the current working
            directory.
        """
        if db_path is None:
            db_path = Path("runtime") / "lab_knowledge.sqlite3"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # -- internal -----------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        # Use DELETE mode instead of WAL for better Windows compatibility
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def close(self) -> None:
        """Close any open database connections and checkpoint WAL."""
        try:
            with self._connect() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass  # Ignore errors during cleanup

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_knowledge (
                    gene TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    event_type TEXT DEFAULT '',
                    delta_psi REAL,
                    fdr REAL,
                    rank INTEGER,
                    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (gene, project_id, event_type)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_gene ON lab_knowledge(gene)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_project ON lab_knowledge(project_id)
                """
            )

    # -- public API ---------------------------------------------------------
    def add_entries(self, project_id: str, entries: list[KnowledgeEntry]) -> int:
        """Add new knowledge entries from a completed project.

        Existing entries for the same (gene, project_id, event_type) are
        silently replaced (upsert semantics).

        Returns the number of entries added/updated.
        """
        if not entries:
            return 0

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO lab_knowledge
                    (gene, project_id, event_type, delta_psi, fdr, rank)
                VALUES (?, ?, COALESCE(?, ''), ?, ?, ?)
                ON CONFLICT(gene, project_id, event_type)
                DO UPDATE SET
                    delta_psi = excluded.delta_psi,
                    fdr = excluded.fdr,
                    rank = excluded.rank,
                    run_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        e.gene,
                        project_id,
                        e.event_type or "",
                        e.delta_psi,
                        e.fdr,
                        e.rank,
                    )
                    for e in entries
                ],
            )
        return len(entries)

    def get_recurrent_genes(
        self, min_projects: int = 2, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Find genes that appeared in at least *min_projects* distinct projects.

        Returns a list of dicts sorted by project count descending:

        .. code-block:: python

            [
                {
                    "gene": "TP53",
                    "project_count": 5,
                    "event_types": ["SE", "MXE"],
                    "avg_delta_psi": 0.25,
                    "total_hits": 8,
                },
                ...
            ]
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    gene,
                    COUNT(DISTINCT project_id) AS project_count,
                    GROUP_CONCAT(DISTINCT event_type) AS event_types_csv,
                    AVG(delta_psi) AS avg_delta_psi,
                    COUNT(*) AS total_hits
                FROM lab_knowledge
                GROUP BY gene
                HAVING project_count >= ?
                ORDER BY project_count DESC, total_hits DESC
                LIMIT ?
                """,
                (min_projects, limit),
            ).fetchall()

        result = []
        for row in rows:
            event_types_str = row["event_types_csv"] or ""
            event_types = sorted(
                {et.strip() for et in event_types_str.split(",") if et.strip()}
            )
            result.append(
                {
                    "gene": row["gene"],
                    "project_count": row["project_count"],
                    "event_types": event_types,
                    "avg_delta_psi": round(row["avg_delta_psi"], 4)
                    if row["avg_delta_psi"]
                    else None,
                    "total_hits": row["total_hits"],
                }
            )
        return result

    def query_gene(self, gene: str) -> list[dict[str, Any]]:
        """Get all historical appearances of a specific gene.

        Returns list of dicts sorted by run_at descending.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    project_id,
                    event_type,
                    delta_psi,
                    fdr,
                    rank,
                    run_at
                FROM lab_knowledge
                WHERE gene = ?
                ORDER BY run_at DESC
                """,
                (gene,),
            ).fetchall()

        return [dict(row) for row in rows]

    def intersect_with_candidates(
        self, candidate_genes: list[str], min_projects: int = 2
    ) -> list[dict[str, Any]]:
        """Return recurrent genes that also appear in the current candidate list.

        This is the main method called by the ``consult_knowledge`` action.
        It finds genes that are both:
        1. In the current analysis's candidate list
        2. Recurrent across past projects (>= min_projects)

        Returns list of recurrent gene info dicts (same format as
        :meth:`get_recurrent_genes`), filtered to only those in
        *candidate_genes*.
        """
        if not candidate_genes:
            return []

        candidate_set = {g.upper() for g in candidate_genes}
        recurrent = self.get_recurrent_genes(min_projects=min_projects)

        # Filter to intersection
        return [r for r in recurrent if r["gene"].upper() in candidate_set]

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics about the knowledge base."""
        with self._connect() as conn:
            total_entries = conn.execute(
                "SELECT COUNT(*) AS cnt FROM lab_knowledge"
            ).fetchone()["cnt"]
            total_genes = conn.execute(
                "SELECT COUNT(DISTINCT gene) AS cnt FROM lab_knowledge"
            ).fetchone()["cnt"]
            total_projects = conn.execute(
                "SELECT COUNT(DISTINCT project_id) AS cnt FROM lab_knowledge"
            ).fetchone()["cnt"]

        return {
            "total_entries": total_entries,
            "unique_genes": total_genes,
            "projects_tracked": total_projects,
        }
