"""Built-in MCP server for SpliceGAIP demos.

Runs a small JSON-over-HTTP MCP endpoint inside the application process so
the AI assistant page always has at least one connected tool provider:
``GET /health``, ``POST /tools/list`` and ``POST /tools/call``.

The same tool implementations are exposed over the standard MCP stdio
transport by :mod:`splicegaip.mcp.splice_server`.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from splicegaip.mcp.demo_tools import TOOL_SPECS, call_tool, text_result

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9100
SERVER_NAME = "splicegaip-builtin"

_server: ThreadingHTTPServer | None = None
_thread: threading.Thread | None = None
_lock = threading.Lock()


class _Handler(BaseHTTPRequestHandler):
    server_version = "SpliceGAIP-MCP/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        if length > 2_000_000:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in ("/health", ""):
            self._send(
                200,
                {
                    "status": "ok",
                    "name": SERVER_NAME,
                    "protocol": "mcp-http",
                    "tools": len(TOOL_SPECS),
                },
            )
            return
        if self.path.rstrip("/") == "/tools/list":
            self._send(200, {"tools": TOOL_SPECS})
            return
        self._send(404, {"error": f"unknown path: {self.path}"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")
        try:
            if path == "/tools/list":
                self._send(200, {"tools": TOOL_SPECS})
                return
            if path == "/tools/call":
                payload = self._read_json()
                tool_name = str(payload.get("name", "")).strip()
                arguments = payload.get("arguments") or {}
                if not tool_name:
                    raise ValueError("name is required")
                if not isinstance(arguments, dict):
                    raise ValueError("arguments must be an object")
                try:
                    result = call_tool(tool_name, arguments)
                except Exception as error:  # noqa: BLE001 - report as MCP tool error
                    self._send(
                        200,
                        {
                            "content": [{"type": "text", "text": f"{type(error).__name__}: {error}"}],
                            "isError": True,
                        },
                    )
                    return
                self._send(
                    200,
                    {
                        "content": [{"type": "text", "text": text_result(result)}],
                        "structuredContent": result,
                        "isError": False,
                    },
                )
                return
            self._send(404, {"error": f"unknown path: {self.path}"})
        except (ValueError, json.JSONDecodeError) as error:
            self._send(400, {"error": str(error)})


def _health_ok(host: str, port: int) -> bool:
    try:
        with urlopen(f"http://{host}:{port}/health", timeout=1.0) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("name") == SERVER_NAME and data.get("status") == "ok"
    except (URLError, OSError, ValueError, json.JSONDecodeError):
        return False


def start_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict[str, Any]:
    """Start the demo server once; returns a status payload."""
    global _server, _thread
    with _lock:
        if _server is not None:
            return {"running": True, "url": f"http://{host}:{port}", "name": SERVER_NAME}
        try:
            httpd = ThreadingHTTPServer((host, port), _Handler)
        except OSError as error:
            if _health_ok(host, port):
                return {
                    "running": True,
                    "external": True,
                    "url": f"http://{host}:{port}",
                    "name": SERVER_NAME,
                }
            return {
                "running": False,
                "url": f"http://{host}:{port}",
                "name": SERVER_NAME,
                "error": str(error),
            }
        httpd.daemon_threads = True
        _thread = threading.Thread(
            target=httpd.serve_forever,
            name="splicegaip-mcp-demo",
            daemon=True,
        )
        _thread.start()
        _server = httpd
        return {"running": True, "url": f"http://{host}:{port}", "name": SERVER_NAME}


def ensure_demo_server() -> dict[str, Any]:
    """Best-effort startup hook; never raises into the API boot path."""
    try:
        return start_server()
    except Exception as error:  # noqa: BLE001
        return {"running": False, "error": str(error), "name": SERVER_NAME}


def stop_server() -> None:
    global _server, _thread
    with _lock:
        if _server is not None:
            _server.shutdown()
            _server.server_close()
            _server = None
        _thread = None
