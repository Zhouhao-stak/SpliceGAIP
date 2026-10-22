"""Tools exposed by the built-in SpliceGAIP MCP server.

The functions are transport-agnostic: the same implementations back the
stdlib HTTP demo server and the standard stdio MCP server, so the UI demos
and the protocol-compliant path always answer identically.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

EVENT_TYPE_GLOSSARY: dict[str, dict[str, str]] = {
    "SE": {
        "name": "Skipped Exon",
        "zh": "外显子跳跃",
        "description": "An exon is included in some transcripts and skipped in others.",
    },
    "MXE": {
        "name": "Mutually Exclusive Exons",
        "zh": "互斥外显子",
        "description": "Two exons are retained in a mutually exclusive manner.",
    },
    "A5SS": {
        "name": "Alternative 5' Splice Site",
        "zh": "可变 5' 剪接位点",
        "description": "Two competing donor sites change the exon 5' boundary.",
    },
    "A3SS": {
        "name": "Alternative 3' Splice Site",
        "zh": "可变 3' 剪接位点",
        "description": "Two competing acceptor sites change the exon 3' boundary.",
    },
    "RI": {
        "name": "Retained Intron",
        "zh": "内含子保留",
        "description": "An intron is retained in a fraction of transcripts.",
    },
}

_SUMMARY_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_SUMMARY_TTL_SECONDS = 20.0


def _settings() -> Any:
    from splicegaip.config import load_prepared_settings

    settings, _ = load_prepared_settings()
    return settings


def _memory() -> Any:
    from splicegaip.memory import ProjectMemory

    settings = _settings()
    return ProjectMemory(settings.paths.memory_db)


def _require_project(project_id: str) -> dict[str, Any]:
    project = _memory().get_project(project_id)
    if project is None:
        available = [item["project_id"] for item in _memory().list_projects()[:5]]
        raise ValueError(
            f"unknown project_id {project_id!r}; available: {', '.join(available) or 'none'}"
        )
    return project


def list_projects() -> dict[str, Any]:
    """列出本机已分析的项目，便于选择 project_id。"""
    projects = _memory().list_projects()
    return {
        "count": len(projects),
        "projects": [
            {
                "project_id": item.get("project_id"),
                "name": item.get("name"),
                "query": item.get("query"),
                "source_format": item.get("source_format"),
                "created_at": item.get("created_at"),
            }
            for item in projects[:20]
        ],
    }


def project_summary(project_id: str) -> dict[str, Any]:
    """返回项目的样本数、事件数、显著事件数和排名靠前的候选基因。"""
    project_id = str(project_id).strip()
    cached = _SUMMARY_CACHE.get(project_id)
    if cached and time.time() - cached[0] < _SUMMARY_TTL_SECONDS:
        return cached[1]

    project = _require_project(project_id)
    settings = _settings()
    gates = settings.analysis
    memory = _memory()

    with closing(sqlite3.connect(settings.paths.memory_db, timeout=30)) as connection:
        connection.row_factory = sqlite3.Row
        event_count = connection.execute(
            "SELECT COUNT(*) FROM events WHERE project_id = ?", (project_id,)
        ).fetchone()[0]
        significant = connection.execute(
            "SELECT COUNT(*) FROM events WHERE project_id = ? AND significant = 1",
            (project_id,),
        ).fetchone()[0]
        single_sample = connection.execute(
            "SELECT COUNT(*) FROM events WHERE project_id = ? AND significant = 1 "
            "AND (inclusion_reads < 10 OR exclusion_reads < 10)",
            (project_id,),
        ).fetchone()[0]
        type_rows = connection.execute(
            "SELECT event_type, COUNT(*) AS n FROM events WHERE project_id = ? "
            "GROUP BY event_type ORDER BY n DESC",
            (project_id,),
        ).fetchall()
        candidate_total = connection.execute(
            "SELECT COUNT(*) FROM candidates WHERE project_id = ?", (project_id,)
        ).fetchone()[0]

    candidates = memory.load_candidates(project_id)[:5]
    enrichment = memory.load_enrichment(project_id)[:5]

    payload = {
        "project_id": project_id,
        "name": project.get("name"),
        "query": project.get("query"),
        "source_format": project.get("source_format"),
        "created_at": project.get("created_at"),
        "samples": len(memory.load_samples(project_id)),
        "events": event_count,
        "significant_events": significant,
        "candidate_genes": candidate_total,
        "quality_flags": {
            "significant_below_read_support": single_sample,
            "fdr_threshold": gates.fdr_threshold,
            "delta_psi_threshold": gates.delta_psi_threshold,
        },
        "event_types": {row["event_type"]: row["n"] for row in type_rows},
        "top_candidates": [
            {
                "rank": item.get("rank"),
                "gene": item.get("gene_symbol") or item.get("gene_id"),
                "event_type": item.get("event_type"),
                "delta_psi": _round(item.get("delta_psi"), 4),
                "fdr": _round(item.get("fdr"), 6),
                "score": _round(item.get("score"), 4),
            }
            for item in candidates
        ],
        "top_enrichment": [
            {
                "ontology": item.get("ontology"),
                "term": item.get("term"),
                "fdr": _round(item.get("fdr"), 6),
                "genes": item.get("gene_count"),
            }
            for item in enrichment
        ],
    }
    _SUMMARY_CACHE[project_id] = (time.time(), payload)
    return payload


def search_events(
    project_id: str,
    gene: str = "",
    event_type: str = "",
    fdr_max: float = 0.05,
    min_abs_dpsi: float = 0.1,
    limit: int = 20,
) -> dict[str, Any]:
    """按基因、事件类型、FDR 和 |ΔPSI| 检索剪接事件。"""
    project_id = str(project_id).strip()
    _require_project(project_id)
    limit = max(1, min(int(limit), 200))
    event_type = str(event_type or "").strip().upper()
    gene = str(gene or "").strip()

    clauses = ["project_id = ?", "fdr IS NOT NULL", "delta_psi IS NOT NULL"]
    params: list[Any] = [project_id]
    if gene:
        clauses.append("(UPPER(gene_symbol) = UPPER(?) OR UPPER(gene_id) = UPPER(?))")
        params.extend([gene, gene])
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    clauses.append("fdr <= ?")
    params.append(float(fdr_max))
    clauses.append("ABS(delta_psi) >= ?")
    params.append(float(min_abs_dpsi))
    params.append(limit)

    query = (
        "SELECT gene_symbol, gene_id, event_type, chromosome, genomic_coordinates, "
        "delta_psi, fdr, mean_psi_group1, mean_psi_group2, total_support_reads "
        "FROM events WHERE " + " AND ".join(clauses) +
        " ORDER BY ABS(delta_psi) DESC, fdr ASC LIMIT ?"
    )
    settings = _settings()
    with closing(sqlite3.connect(settings.paths.memory_db, timeout=30)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

    return {
        "project_id": project_id,
        "filters": {
            "gene": gene or None,
            "event_type": event_type or None,
            "fdr_max": float(fdr_max),
            "min_abs_dpsi": float(min_abs_dpsi),
        },
        "count": len(rows),
        "events": [
            {
                "gene": row["gene_symbol"] or row["gene_id"],
                "event_type": row["event_type"],
                "chromosome": row["chromosome"],
                "coordinates": row["genomic_coordinates"],
                "delta_psi": _round(row["delta_psi"], 4),
                "fdr": _round(row["fdr"], 6),
                "psi_group1": _round(row["mean_psi_group1"], 4),
                "psi_group2": _round(row["mean_psi_group2"], 4),
                "support_reads": row["total_support_reads"],
            }
            for row in rows
        ],
    }


def explain_event_type(event_type: str) -> dict[str, Any]:
    """解释 SE/MXE/A5SS/A3SS/RI 五种可变剪接事件类型。"""
    key = str(event_type or "").strip().upper()
    if key:
        info = EVENT_TYPE_GLOSSARY.get(key)
        if info is None:
            return {"error": f"unknown event_type {key!r}", "supported": list(EVENT_TYPE_GLOSSARY)}
        return {"event_type": key, **info}
    return {"event_types": [{"event_type": key, **value} for key, value in EVENT_TYPE_GLOSSARY.items()]}


def compute_delta_psi(group1_psi: float, group2_psi: float) -> dict[str, Any]:
    """计算 ΔPSI = group2 − group1 并给出方向解释。"""
    group1 = float(group1_psi)
    group2 = float(group2_psi)
    if not 0.0 <= group1 <= 1.0 or not 0.0 <= group2 <= 1.0:
        raise ValueError("PSI values must be between 0 and 1")
    delta = group2 - group1
    if abs(delta) < 0.1:
        direction = "no meaningful shift (|ΔPSI| < 0.1)"
        zh = "无实质变化（|ΔPSI| < 0.1）"
    elif delta > 0:
        direction = "more inclusion in group2"
        zh = "group2 中外显子/片段包含比例升高"
    else:
        direction = "less inclusion in group2"
        zh = "group2 中外显子/片段包含比例降低"
    return {
        "group1_psi": group1,
        "group2_psi": group2,
        "delta_psi": round(delta, 4),
        "direction": direction,
        "interpretation_zh": zh,
    }


def _round(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "list_projects",
        "description": "列出本机已分析的 SpliceGAIP 项目及 project_id。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "project_summary",
        "description": "汇总一个项目的样本数、事件数、显著事件、候选基因和通路富集。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID，例如 SPN-XXXX"}
            },
            "required": ["project_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_events",
        "description": "按基因、事件类型、FDR 与 |ΔPSI| 检索剪接事件，返回位点和效应量。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "项目 ID"},
                "gene": {"type": "string", "description": "基因符号，如 CD44；留空表示全部"},
                "event_type": {
                    "type": "string",
                    "enum": ["", "SE", "MXE", "A5SS", "A3SS", "RI"],
                    "description": "事件类型；留空表示全部",
                },
                "fdr_max": {"type": "number", "default": 0.05, "description": "FDR 上限"},
                "min_abs_dpsi": {
                    "type": "number",
                    "default": 0.1,
                    "description": "最小 |ΔPSI|",
                },
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 200},
            },
            "required": ["project_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "explain_event_type",
        "description": "解释 SE、MXE、A5SS、A3SS、RI 五种可变剪接事件类型。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "留空返回全部类型",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "compute_delta_psi",
        "description": "计算 ΔPSI = group2 − group1，并解释剪接包含比例的变化方向。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group1_psi": {"type": "number", "minimum": 0, "maximum": 1},
                "group2_psi": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["group1_psi", "group2_psi"],
            "additionalProperties": False,
        },
    },
]

TOOL_FUNCTIONS = {
    "list_projects": list_projects,
    "project_summary": project_summary,
    "search_events": search_events,
    "explain_event_type": explain_event_type,
    "compute_delta_psi": compute_delta_psi,
}


def call_tool(tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a demo tool by name; raises for unknown tools/arguments."""
    function = TOOL_FUNCTIONS.get(tool_name)
    if function is None:
        raise ValueError(f"unknown tool: {tool_name}")
    kwargs = dict(arguments or {})
    allowed = set(TOOL_SPECS_BY_NAME[tool_name]["inputSchema"].get("properties", {}))
    unexpected = set(kwargs) - allowed
    if unexpected:
        raise ValueError(f"unexpected arguments: {', '.join(sorted(unexpected))}")
    return function(**kwargs)


TOOL_SPECS_BY_NAME = {spec["name"]: spec for spec in TOOL_SPECS}


def text_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
