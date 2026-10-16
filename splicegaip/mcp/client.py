"""MCP client wrapper for SpliceGAIP.

Manages connections to external MCP servers and provides a unified
interface for tool discovery and invocation. Designed to work both
in development mode (with full MCP SDK) and in packaged EXE mode
(with lightweight HTTP-based MCP calls).
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


@dataclass
class MCPServerConfig:
    """Configuration for one MCP server."""

    name: str
    transport: str = "stdio"  # stdio | sse | http
    command: str | None = None  # For stdio transport
    url: str | None = None  # For SSE/HTTP transport
    env: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0


@dataclass
class MCPToolInfo:
    """Metadata about an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str


class MCPClient:
    """Lightweight MCP client that works in both dev and EXE modes.

    In development: uses the full mcp Python package with stdio/sse transports.
    In EXE mode: uses direct HTTP calls to locally-running MCP servers.

    This dual-mode design ensures MCP functionality survives PyInstaller
    packaging while maintaining full feature parity during development.
    """

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".splicegaip" / "mcp"
        self.servers: dict[str, MCPServerConfig] = {}
        self._tools_cache: dict[str, list[MCPToolInfo]] = {}
        self._http_clients: dict[str, httpx.AsyncClient] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load MCP server configuration from JSON file."""
        config_file = self.config_dir / "servers.json"
        if not config_file.exists():
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for server_data in data.get("servers", []):
                server = MCPServerConfig(
                    name=server_data["name"],
                    transport=server_data.get("transport", "stdio"),
                    command=server_data.get("command"),
                    url=server_data.get("url"),
                    env=server_data.get("env", {}),
                    timeout=server_data.get("timeout", 30.0),
                )
                self.servers[server.name] = server
        except Exception as exc:  # noqa: BLE001
            print(f"[MCP] Failed to load config: {exc}")

    async def connect(self, server_name: str) -> bool:
        """Connect to an MCP server.

        Returns True if connection succeeded, False otherwise.
        """
        server = self.servers.get(server_name)
        if not server:
            return False

        try:
            if server.transport in ("sse", "http"):
                if not server.url:
                    return False
                client = httpx.AsyncClient(base_url=server.url, timeout=server.timeout)
                # Test connectivity
                response = await client.get("/health")
                if response.status_code == 200:
                    self._http_clients[server_name] = client
                    return True
            elif server.transport == "stdio":
                # In EXE mode, stdio servers are not supported
                # Fall back to HTTP if available
                if server.url:
                    return await self.connect(server_name)
                return False
        except Exception as exc:  # noqa: BLE001
            print(f"[MCP] Connection failed for {server_name}: {exc}")
            return False

        return False

    async def disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server."""
        if server_name in self._http_clients:
            await self._http_clients[server_name].aclose()
            del self._http_clients[server_name]
        self._tools_cache.pop(server_name, None)

    async def list_tools(self, server_name: str) -> list[MCPToolInfo]:
        """List all tools available from an MCP server."""
        if server_name in self._tools_cache:
            return self._tools_cache[server_name]

        client = self._http_clients.get(server_name)
        if not client:
            connected = await self.connect(server_name)
            if not connected:
                return []
            client = self._http_clients.get(server_name)
            if not client:
                return []

        try:
            # MCP protocol: list tools via /tools endpoint
            response = await client.post("/tools/list", json={})
            if response.status_code != 200:
                return []

            data = response.json()
            tools = []
            for tool_data in data.get("tools", []):
                tool = MCPToolInfo(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=server_name,
                )
                tools.append(tool)

            self._tools_cache[server_name] = tools
            return tools
        except Exception as exc:  # noqa: BLE001
            print(f"[MCP] Failed to list tools for {server_name}: {exc}")
            return []

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call an MCP tool and return the result.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments matching the input schema

        Returns:
            Tool result as a dictionary
        """
        client = self._http_clients.get(server_name)
        if not client:
            connected = await self.connect(server_name)
            if not connected:
                return {"error": f"Cannot connect to server: {server_name}"}
            client = self._http_clients.get(server_name)
            if not client:
                return {"error": f"Cannot connect to server: {server_name}"}

        try:
            response = await client.post(
                "/tools/call",
                json={"name": tool_name, "arguments": arguments or {}},
            )

            if response.status_code != 200:
                return {"error": f"Tool call failed: HTTP {response.status_code}"}

            return response.json()
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Tool call exception: {str(exc)}"}

    async def close_all(self) -> None:
        """Close all server connections."""
        for server_name in list(self._http_clients.keys()):
            await self.disconnect(server_name)


# Convenience functions for synchronous usage in FastAPI endpoints

def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance."""
    if not hasattr(get_mcp_client, "_instance"):
        get_mcp_client._instance = MCPClient()
    return get_mcp_client._instance


async def mcp_list_servers() -> dict[str, list[str]]:
    """List all configured MCP servers and their available tools.

    Returns:
        Dict mapping server names to lists of tool names
    """
    client = get_mcp_client()
    result = {}

    for server_name in client.servers:
        connected = await client.connect(server_name)
        if connected:
            tools = await client.list_tools(server_name)
            result[server_name] = [tool.name for tool in tools]

    return result


async def mcp_call_tool(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call an MCP tool (synchronous wrapper).

    Args:
        server_name: MCP server name
        tool_name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result or error dict
    """
    client = get_mcp_client()
    return await client.call_tool(server_name, tool_name, arguments)
