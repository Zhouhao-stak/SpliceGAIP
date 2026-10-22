"""MCP client wrapper for SpliceGAIP.

Supports the official Model Context Protocol transports (``stdio``, ``sse``
and ``streamable-http``) through the ``mcp`` SDK, plus a tiny JSON-over-HTTP
adapter for the built-in demo server so the feature also works in packaged
builds where spawning Python subprocesses is not practical.

SDK sessions are intentionally short-lived: each probe/list/call opens a
session, finishes, and closes it inside the same asyncio task. Holding an
anyio-based MCP session across FastAPI requests triggers cancel-scope errors
and makes cleanup depend on request scheduling.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

import httpx

BUILTIN_SERVER_NAME = "splicegaip-builtin"
BUILTIN_SERVER_URL = "http://127.0.0.1:9100"


@dataclass
class MCPServerConfig:
    """Configuration for one MCP server."""

    name: str
    transport: str = "stdio"  # stdio | sse | http (streamable-http)
    command: str | None = None  # For stdio transport
    args: list[str] = field(default_factory=list)
    url: str | None = None  # For sse/http transport
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    timeout: float = 30.0
    # auto: try official MCP first, then the simple /tools JSON adapter
    # simple: only the built-in /health + /tools/list + /tools/call adapter
    # mcp: only the official MCP SDK transports
    protocol: str = "auto"
    enabled: bool = True
    builtin: bool = False


@dataclass
class MCPToolInfo:
    """Metadata about an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str


class MCPClient:
    """MCP client that works with standard servers and the built-in adapter."""

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".splicegaip" / "mcp"
        self.config_path = self.config_dir / "servers.json"
        self.servers: dict[str, MCPServerConfig] = {}
        self._tools_cache: dict[str, list[MCPToolInfo]] = {}
        self._http_clients: dict[str, httpx.AsyncClient] = {}
        self._sdk_ready: set[str] = set()
        self._sdk_urls: dict[str, str] = {}
        self._connected_via: dict[str, str] = {}
        self._load_config()

    # -- configuration ----------------------------------------------------
    def _load_config(self) -> None:
        """Load MCP server configuration from JSON file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                for server_data in data.get("servers", []):
                    name = str(server_data.get("name", "")).strip()
                    if not name:
                        continue
                    self.servers[name] = MCPServerConfig(
                        name=name,
                        transport=str(server_data.get("transport", "stdio")).lower(),
                        command=server_data.get("command"),
                        args=list(server_data.get("args", []) or []),
                        url=server_data.get("url"),
                        env=dict(server_data.get("env", {}) or {}),
                        cwd=server_data.get("cwd"),
                        timeout=float(server_data.get("timeout", 30.0)),
                        protocol=str(server_data.get("protocol", "auto")).lower(),
                        enabled=bool(server_data.get("enabled", True)),
                        builtin=bool(server_data.get("builtin", False)),
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"[MCP] Failed to load config: {exc}")

        # The in-process demo server is always available, even without a config.
        self.servers.setdefault(
            BUILTIN_SERVER_NAME,
            MCPServerConfig(
                name=BUILTIN_SERVER_NAME,
                transport="http",
                url=BUILTIN_SERVER_URL,
                protocol="simple",
                timeout=10.0,
                builtin=True,
            ),
        )

    # -- official MCP SDK sessions ---------------------------------------
    @asynccontextmanager
    async def _open_sdk_session(
        self,
        server: MCPServerConfig,
        url: str | None = None,
    ) -> AsyncIterator[Any]:
        try:
            from mcp import ClientSession
        except ImportError as error:
            raise RuntimeError(
                "the 'mcp' SDK is not installed; standard MCP servers are unavailable"
            ) from error

        transport = server.transport.replace("_", "-")
        if transport == "stdio":
            if not server.command:
                raise ValueError("stdio server requires a command")
            from mcp.client.stdio import StdioServerParameters, stdio_client

            params = StdioServerParameters(
                command=server.command,
                args=server.args,
                env={**os.environ, **server.env},
                cwd=server.cwd or None,
            )
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await asyncio.wait_for(session.initialize(), timeout=server.timeout)
                    yield session
            return

        if transport == "sse":
            from mcp.client.sse import sse_client

            target = url or server.url
            if not target:
                raise ValueError("sse server requires a url")
            async with sse_client(target, timeout=server.timeout) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await asyncio.wait_for(session.initialize(), timeout=server.timeout)
                    yield session
            return

        if not (url or server.url):
            raise ValueError("http server requires a url")
        try:
            from mcp.client.streamable_http import (
                streamable_http_client as open_transport,
            )
        except ImportError:
            from mcp.client.streamable_http import (
                streamablehttp_client as open_transport,  # type: ignore[no-redef]
            )
        target = url or server.url
        assert target is not None
        async with open_transport(target) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await asyncio.wait_for(
                    session.initialize(), timeout=min(server.timeout, 15.0)
                )
                yield session

    @staticmethod
    def _sdk_tools(server_name: str, result: Any) -> list[MCPToolInfo]:
        return [
            MCPToolInfo(
                name=tool.name,
                description=getattr(tool, "description", "") or "",
                input_schema=(
                    getattr(tool, "inputSchema", None)
                    or getattr(tool, "input_schema", None)
                    or {}
                ),
                server_name=server_name,
            )
            for tool in getattr(result, "tools", [])
        ]

    async def _probe_sdk(
        self,
        server: MCPServerConfig,
        mode: str,
        url: str | None = None,
    ) -> bool:
        try:
            async with self._open_sdk_session(server, url=url) as session:
                result = await session.list_tools()
            self._tools_cache[server.name] = self._sdk_tools(server.name, result)
        except Exception as exc:  # noqa: BLE001
            print(f"[MCP] SDK probe failed for {server.name}: {exc}")
            self._sdk_ready.discard(server.name)
            return False
        self._sdk_ready.add(server.name)
        self._connected_via[server.name] = mode
        if url:
            self._sdk_urls[server.name] = url
        return True

    # -- connection -------------------------------------------------------
    async def connect(self, server_name: str) -> bool:
        """Probe a configured MCP server. Returns True on success."""
        server = self.servers.get(server_name)
        if server is None or not server.enabled:
            return False
        if server_name in self._http_clients or server_name in self._sdk_ready:
            return True

        transport = server.transport.replace("_", "-")
        try:
            if transport == "stdio":
                return await self._probe_sdk(server, "mcp-stdio")
            if transport == "sse":
                return await self._probe_sdk(server, "mcp-sse")
            if transport in ("http", "streamable-http", "simple"):
                return await self._connect_http(server)
        except Exception as exc:  # noqa: BLE001
            print(f"[MCP] Connection failed for {server_name}: {exc}")
        return False

    async def _connect_http(self, server: MCPServerConfig) -> bool:
        if not server.url:
            return False

        if server.protocol in ("auto", "mcp"):
            candidates = [server.url]
            if not server.url.rstrip("/").endswith("/mcp"):
                candidates.append(server.url.rstrip("/") + "/mcp")
            for url in candidates:
                if await self._probe_sdk(server, "mcp-http", url=url):
                    return True
            if server.protocol == "mcp":
                return False

        client = httpx.AsyncClient(base_url=server.url, timeout=server.timeout)
        try:
            response = await client.get("/health")
            if response.status_code == 200:
                self._http_clients[server.name] = client
                self._connected_via[server.name] = "simple-http"
                return True
        except Exception as exc:  # noqa: BLE001
            print(f"[MCP] Connection failed for {server.name}: {exc}")
        await client.aclose()
        return False

    async def disconnect(self, server_name: str) -> None:
        """Forget a server's connection state and cached tools."""
        client = self._http_clients.pop(server_name, None)
        if client is not None:
            await client.aclose()
        self._sdk_ready.discard(server_name)
        self._sdk_urls.pop(server_name, None)
        self._tools_cache.pop(server_name, None)
        self._connected_via.pop(server_name, None)

    async def refresh(self, server_name: str) -> bool:
        await self.disconnect(server_name)
        return await self.connect(server_name)

    # -- tools ------------------------------------------------------------
    async def list_tools(self, server_name: str) -> list[MCPToolInfo]:
        """List all tools available from an MCP server."""
        if server_name in self._tools_cache:
            return self._tools_cache[server_name]

        server = self.servers.get(server_name)
        if server is None:
            return []

        if server_name in self._sdk_ready:
            try:
                async with self._open_sdk_session(
                    server, url=self._sdk_urls.get(server_name)
                ) as session:
                    result = await session.list_tools()
                tools = self._sdk_tools(server_name, result)
                self._tools_cache[server_name] = tools
                return tools
            except Exception as exc:  # noqa: BLE001
                print(f"[MCP] Failed to list tools for {server_name}: {exc}")
                return []

        client = self._http_clients.get(server_name)
        if client is None:
            if not await self.connect(server_name):
                return []
            client = self._http_clients.get(server_name)
            if client is None:
                # SDK servers cache their tools during connect().
                return self._tools_cache.get(server_name, [])

        try:
            response = await client.post("/tools/list", json={})
            if response.status_code != 200:
                return []
            data = response.json()
            tools = [
                MCPToolInfo(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=server_name,
                )
                for tool_data in data.get("tools", [])
            ]
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
        """Call an MCP tool and return a JSON-serialisable result."""
        server = self.servers.get(server_name)
        if server is None or not server.enabled:
            return {"error": f"Unknown or disabled server: {server_name}"}

        if server_name not in self._sdk_ready and server_name not in self._http_clients:
            if not await self.connect(server_name):
                return {"error": f"Cannot connect to server: {server_name}"}

        if server_name in self._sdk_ready:
            try:
                async with self._open_sdk_session(
                    server, url=self._sdk_urls.get(server_name)
                ) as session:
                    result = await session.call_tool(tool_name, arguments or {})
                payload = self._normalise_payload(self._serialise_result(result))
                if payload.get("isError"):
                    return {"error": self._result_text(payload), "result": payload}
                return payload
            except Exception as exc:  # noqa: BLE001
                return {"error": f"Tool call exception: {exc}"}

        client = self._http_clients.get(server_name)
        if client is None:
            return {"error": f"Cannot connect to server: {server_name}"}
        try:
            response = await client.post(
                "/tools/call",
                json={"name": tool_name, "arguments": arguments or {}},
            )
            if response.status_code != 200:
                detail = response.text[:300]
                return {"error": f"Tool call failed: HTTP {response.status_code} {detail}"}
            payload = response.json()
            if isinstance(payload, dict) and payload.get("isError"):
                return {"error": self._result_text(payload), "result": payload}
            return payload
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Tool call exception: {exc}"}

    @staticmethod
    def _normalise_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """Expose the same keys for SDK (snake_case) and simple-HTTP results."""
        if "structuredContent" not in payload and "structured_content" in payload:
            payload["structuredContent"] = payload["structured_content"]
        if "isError" not in payload and "is_error" in payload:
            payload["isError"] = bool(payload["is_error"])
        structured = payload.get("structuredContent")
        # MCPServer may wrap a dict return as {"result": "<json string>"}.
        if isinstance(structured, dict) and set(structured) == {"result"}:
            inner = structured["result"]
            if isinstance(inner, str):
                try:
                    payload["structuredContent"] = json.loads(inner)
                except json.JSONDecodeError:
                    pass
        return payload

    @staticmethod
    def _serialise_result(result: Any) -> dict[str, Any]:
        if hasattr(result, "model_dump"):
            try:
                data = result.model_dump(mode="json", exclude_none=True)
            except TypeError:
                data = result.model_dump()
            if isinstance(data, dict):
                return data
        if isinstance(result, dict):
            return result
        return {"content": [{"type": "text", "text": str(result)}]}

    @staticmethod
    def _result_text(payload: dict[str, Any]) -> str:
        parts = [
            str(item.get("text", ""))
            for item in payload.get("content", [])
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        text = "\n".join(part for part in parts if part)
        if text:
            return text
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def close_all(self) -> None:
        """Close all HTTP connections and reset SDK flags."""
        for server_name in list(self._http_clients) + list(self._sdk_ready):
            await self.disconnect(server_name)


# Convenience functions for synchronous usage in FastAPI endpoints

def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance."""
    if not hasattr(get_mcp_client, "_instance"):
        get_mcp_client._instance = MCPClient()
    return get_mcp_client._instance


async def mcp_list_servers() -> dict[str, list[str]]:
    """List configured MCP servers and their tool names (connected only)."""
    client = get_mcp_client()
    result: dict[str, list[str]] = {}
    for server_name in client.servers:
        if await client.connect(server_name):
            tools = await client.list_tools(server_name)
            result[server_name] = [tool.name for tool in tools]
    return result


async def mcp_call_tool(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call an MCP tool through the shared client."""
    client = get_mcp_client()
    return await client.call_tool(server_name, tool_name, arguments)
