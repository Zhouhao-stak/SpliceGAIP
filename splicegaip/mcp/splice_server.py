"""Standard MCP stdio server exposing SpliceGAIP project tools.

Run with ``python -m splicegaip.mcp.splice_server``. It speaks the official
Model Context Protocol over stdin/stdout, so any MCP-compatible client can
list and call these tools without knowing anything about SpliceGAIP.
"""

from __future__ import annotations

from splicegaip.mcp.demo_tools import (
    EVENT_TYPE_GLOSSARY,
    compute_delta_psi as _compute_delta_psi,
    explain_event_type as _explain_event_type,
    list_projects as _list_projects,
    project_summary as _project_summary,
    search_events as _search_events,
)

try:  # mcp >= 2 renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as _ServerClass
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _ServerClass  # type: ignore[assignment]


server = _ServerClass(
    "splicegaip-tools",
    instructions=(
        "Tools for inspecting SpliceGAIP alternative-splicing projects: project "
        "summaries, candidate events, event-type definitions and delta-PSI maths."
    ),
)


@server.tool()
def list_projects() -> dict:
    """List analyzed SpliceGAIP projects with their project_id."""
    return _list_projects()


@server.tool()
def project_summary(project_id: str) -> dict:
    """Summarize one project: samples, events, significant hits, top candidates."""
    return _project_summary(project_id)


@server.tool()
def search_events(
    project_id: str,
    gene: str = "",
    event_type: str = "",
    fdr_max: float = 0.05,
    min_abs_dpsi: float = 0.1,
    limit: int = 20,
) -> dict:
    """Search splicing events by gene, type, FDR and absolute delta PSI."""
    return _search_events(
        project_id=project_id,
        gene=gene,
        event_type=event_type,
        fdr_max=fdr_max,
        min_abs_dpsi=min_abs_dpsi,
        limit=limit,
    )


@server.tool()
def explain_event_type(event_type: str = "") -> dict:
    """Explain SE, MXE, A5SS, A3SS and RI event types (empty returns all)."""
    if not event_type.strip():
        return {"event_types": EVENT_TYPE_GLOSSARY}
    return _explain_event_type(event_type)


@server.tool()
def compute_delta_psi(group1_psi: float, group2_psi: float) -> dict:
    """Compute delta PSI = group2 - group1 and interpret the direction."""
    return _compute_delta_psi(group1_psi, group2_psi)


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
