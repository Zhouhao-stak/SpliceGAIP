"""Analysis Memory: durable project state in SQLite.

Persists everything the prompt requires an analysis to remember:

* input data fingerprint
* analysis plan
* generated code / parameters
* results (events, candidates, enrichment, figures)
* interpretation and report artifacts
* workflow logs (agent-by-agent trace)
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    source_dir TEXT,
    source_format TEXT,
    species TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS samples (
    project_id TEXT NOT NULL,
    sample_id TEXT NOT NULL,
    group_name TEXT NOT NULL,
    condition TEXT,
    tissue TEXT,
    batch TEXT,
    PRIMARY KEY (project_id, sample_id)
);

CREATE TABLE IF NOT EXISTS events (
    project_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    gene_id TEXT,
    gene_symbol TEXT,
    event_type TEXT,
    chromosome TEXT,
    strand TEXT,
    genomic_coordinates TEXT,
    source_tool TEXT,
    mean_psi_group1 REAL,
    mean_psi_group2 REAL,
    delta_psi REAL,
    p_value REAL,
    fdr REAL,
    inclusion_reads INTEGER,
    exclusion_reads INTEGER,
    total_support_reads INTEGER,
    psi_json TEXT,
    significant INTEGER,
    PRIMARY KEY (project_id, event_id)
);

CREATE TABLE IF NOT EXISTS candidates (
    project_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    gene_id TEXT,
    gene_symbol TEXT,
    event_type TEXT,
    delta_psi REAL,
    fdr REAL,
    score REAL,
    components_json TEXT,
    evidence_json TEXT,
    PRIMARY KEY (project_id, rank)
);

CREATE TABLE IF NOT EXISTS enrichment_terms (
    project_id TEXT NOT NULL,
    ontology TEXT NOT NULL,
    term TEXT NOT NULL,
    gene_count INTEGER,
    background_count INTEGER,
    fold_enrichment REAL,
    p_value REAL,
    fdr REAL,
    genes_json TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    project_id TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interpretations (
    project_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProjectMemory:
    """SQLite-backed analysis memory (thread-safe)."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    # -- projects ---------------------------------------------------------
    def create_project(
        self,
        project_id: str,
        name: str,
        query: str,
        source_dir: str = "",
        source_format: str = "",
        species: str = "",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO projects "
                "(project_id, name, query, source_dir, source_format, species, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project_id, name, query, source_dir, source_format, species, _utc_now()),
            )

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM projects ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    # -- samples ----------------------------------------------------------
    def save_samples(self, project_id: str, samples: Sequence[Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM samples WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT INTO samples (project_id, sample_id, group_name, condition, tissue, batch) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        project_id,
                        sample.sample_id,
                        sample.group,
                        sample.condition,
                        sample.tissue,
                        sample.batch,
                    )
                    for sample in samples
                ],
            )

    def load_samples(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM samples WHERE project_id = ? ORDER BY sample_id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    # -- events -----------------------------------------------------------
    def save_events(
        self,
        project_id: str,
        events: Sequence[Any],
        significant_ids: set[str] | None = None,
    ) -> None:
        significant_ids = significant_ids or set()
        with self._connect() as connection:
            connection.execute("DELETE FROM events WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT OR REPLACE INTO events (project_id, event_id, gene_id, gene_symbol, "
                "event_type, chromosome, strand, genomic_coordinates, source_tool, "
                "mean_psi_group1, mean_psi_group2, delta_psi, p_value, fdr, inclusion_reads, "
                "exclusion_reads, total_support_reads, psi_json, significant) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        project_id,
                        event.event_id,
                        event.gene_id,
                        event.gene_symbol,
                        event.event_type,
                        event.chromosome,
                        event.strand,
                        event.genomic_coordinates,
                        event.source_tool,
                        event.mean_psi_group1,
                        event.mean_psi_group2,
                        event.delta_psi,
                        event.p_value,
                        event.fdr,
                        event.inclusion_reads,
                        event.exclusion_reads,
                        event.total_support_reads,
                        json.dumps(event.psi_by_sample),
                        1 if event.event_id in significant_ids else 0,
                    )
                    for event in events
                ],
            )

    def load_events(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE project_id = ? ORDER BY event_id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    # -- candidates -------------------------------------------------------
    def save_candidates(self, project_id: str, candidates: Sequence[Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM candidates WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT INTO candidates (project_id, rank, event_id, gene_id, gene_symbol, "
                "event_type, delta_psi, fdr, score, components_json, evidence_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        project_id,
                        rank,
                        candidate.event_id,
                        candidate.gene_id,
                        candidate.gene_symbol,
                        candidate.event_type,
                        candidate.delta_psi,
                        candidate.fdr,
                        candidate.score,
                        json.dumps(
                            {
                                "significance": candidate.significance_component,
                                "effect": candidate.effect_component,
                                "biology": candidate.biology_component,
                                "literature": candidate.literature_component,
                            }
                        ),
                        json.dumps(list(candidate.evidence)),
                    )
                    for rank, candidate in enumerate(candidates, start=1)
                ],
            )

    def load_candidates(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM candidates WHERE project_id = ? ORDER BY rank", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    # -- enrichment -------------------------------------------------------
    def save_enrichment(self, project_id: str, results: Sequence[Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM enrichment_terms WHERE project_id = ?", (project_id,))
            connection.executemany(
                "INSERT INTO enrichment_terms (project_id, ontology, term, gene_count, "
                "background_count, fold_enrichment, p_value, fdr, genes_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        project_id,
                        result.ontology,
                        result.term,
                        result.gene_count,
                        result.background_count,
                        result.fold_enrichment,
                        result.p_value,
                        result.fdr,
                        json.dumps(list(result.genes)),
                    )
                    for result in results
                ],
            )

    def load_enrichment(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM enrichment_terms WHERE project_id = ? ORDER BY fdr", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    # -- artifacts / plans / interpretations / logs -----------------------
    def save_artifact(self, project_id: str, kind: str, path: str | Path) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO artifacts (project_id, kind, path, created_at) VALUES (?, ?, ?, ?)",
                (project_id, kind, str(path), _utc_now()),
            )

    def load_artifacts(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def save_plan(self, project_id: str, plan: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM plans WHERE project_id = ?", (project_id,))
            connection.execute(
                "INSERT INTO plans (project_id, plan_json, created_at) VALUES (?, ?, ?)",
                (project_id, json.dumps(plan), _utc_now()),
            )

    def load_plan(self, project_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT plan_json FROM plans WHERE project_id = ?", (project_id,)
            ).fetchone()
        return json.loads(row["plan_json"]) if row else None

    def save_interpretation(self, project_id: str, agent: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO interpretations (project_id, agent, content, created_at) "
                "VALUES (?, ?, ?, ?)",
                (project_id, agent, content, _utc_now()),
            )

    def load_interpretations(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM interpretations WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def log(
        self,
        project_id: str,
        agent: str,
        action: str,
        status: str = "ok",
        detail: str = "",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO workflow_logs (project_id, agent, action, status, detail, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, agent, action, status, detail[:4000], _utc_now()),
            )

    def load_logs(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_logs WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]
