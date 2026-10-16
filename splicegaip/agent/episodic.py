"""Episodic memory: what the agent learned from previous runs.

The analysis memory stores *results*; this store keeps *decisions and their
outcomes*, keyed by a coarse dataset signature. Next time a similar dataset
arrives, the agent can start from thresholds that worked before instead of
re-deriving them from scratch.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_format TEXT,
    event_count INTEGER,
    action TEXT NOT NULL,
    args_json TEXT,
    status TEXT NOT NULL,
    message TEXT,
    significant INTEGER,
    params_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_episodes_action ON agent_episodes(action);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EpisodicMemory:
    """SQLite-backed store of agent decisions and their outcomes."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    # -- schema -----------------------------------------------------------
    def ensure(self) -> bool:
        """Create the table; ``False`` when the location is unusable."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path, timeout=5.0) as connection:
                connection.executescript(SCHEMA)
            return True
        except Exception:  # noqa: BLE001 - memory is optional infrastructure
            return False

    # -- write ------------------------------------------------------------
    def record(
        self,
        *,
        project_id: str,
        source_format: str,
        event_count: int,
        action: str,
        args: dict[str, Any],
        status: str,
        message: str,
        significant: int | None,
        params: dict[str, Any],
    ) -> None:
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as connection:
                connection.execute(
                    "INSERT INTO agent_episodes "
                    "(project_id, created_at, source_format, event_count, action, args_json, "
                    " status, message, significant, params_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        project_id,
                        _now(),
                        source_format,
                        int(event_count or 0),
                        action,
                        json.dumps(args, ensure_ascii=False)[:2000],
                        status,
                        (message or "")[:1000],
                        significant,
                        json.dumps(params, ensure_ascii=False)[:2000],
                    ),
                )
        except Exception:  # noqa: BLE001 - never break a run over memory
            return

    # -- read -------------------------------------------------------------
    def suggest_params(self, source_format: str, event_count: int) -> dict[str, Any] | None:
        """Parameters that produced a non-empty result on comparable data.

        "Comparable" means the same input format and an event count within
        one order of magnitude. The most recent successful episode wins.
        """
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as connection:
                rows = connection.execute(
                    "SELECT params_json, significant, event_count FROM agent_episodes "
                    "WHERE action IN ('adapt_thresholds', 'filter_significant_events') "
                    "  AND status = 'ok' AND significant IS NOT NULL AND significant > 0 "
                    "ORDER BY id DESC LIMIT 200"
                ).fetchall()
        except Exception:  # noqa: BLE001
            return None
        for raw_params, significant, past_events in rows:
            if not raw_params:
                continue
            try:
                params = json.loads(raw_params)
            except ValueError:
                continue
            if not isinstance(params, dict) or "fdr" not in params:
                continue
            if past_events and event_count:
                ratio = max(past_events, event_count) / max(min(past_events, event_count), 1)
                if ratio > 10:
                    continue
            if source_format and params.get("source_format") not in (None, source_format):
                continue
            return params
        return None

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Most recent episodes (for UI/debug)."""
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as connection:
                rows = connection.execute(
                    "SELECT project_id, created_at, action, status, significant, source_format "
                    "FROM agent_episodes ORDER BY id DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        except Exception:  # noqa: BLE001
            return []
        return [
            {
                "project_id": row[0],
                "created_at": row[1],
                "action": row[2],
                "status": row[3],
                "significant": row[4],
                "source_format": row[5],
            }
            for row in rows
        ]
