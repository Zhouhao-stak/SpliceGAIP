"""MCP (Model Context Protocol) integration for SpliceGAIP.

Provides runtime access to external MCP servers for:
- Web search and information retrieval
- Gene/splicing database queries (Ensembl, UCSC)
- Literature search (PubMed, Europe PMC)
- Browser automation for data extraction
"""

from splicegaip.mcp.client import MCPClient

__all__ = ["MCPClient"]
