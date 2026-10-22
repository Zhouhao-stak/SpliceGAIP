"""FastAPI application: upload / analyze / status / report."""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from splicegaip.analysis import extra_figures
from splicegaip.config import ensure_runtime_dirs, load_prepared_settings
from splicegaip.interface.web_ui import render as render_web_ui
from splicegaip.pipeline import list_projects, project_status, run_analysis
from splicegaip.observability import (
    configure_logging,
    new_request_id,
    reset_request_id,
    set_request_id,
)

API_VERSION = "0.1.0"
logger = logging.getLogger(__name__)

# Dark-navy plate with the BMW-blue accent bar — same marks as the UI header.
# Served as a real endpoint because browsers probe /favicon.ico unconditionally
# and a 404 there shows up as a console error.
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" fill="#1a2129"/>'
    '<rect y="28" width="32" height="4" fill="#1c69d4"/>'
    '<text x="16" y="21" font-family="Segoe UI, sans-serif" font-size="13"'
    ' font-weight="700" fill="#ffffff" text-anchor="middle">SG</text>'
    "</svg>"
)


def _with_overrides(settings: Any, thresholds: Any) -> Any:
    """Return settings with optional per-request analysis thresholds applied.

    The UI exposes FDR / |delta PSI| / min reads / min samples / top-N as
    "advanced parameters"; anything not supplied keeps the configured value.
    """
    if not isinstance(thresholds, dict) or not thresholds:
        return settings
    import dataclasses

    analysis = settings.analysis
    mapping = {
        "fdr": "fdr_threshold",
        "fdr_threshold": "fdr_threshold",
        "delta_psi": "delta_psi_threshold",
        "delta_psi_threshold": "delta_psi_threshold",
        "min_support_reads": "min_support_reads",
        "min_valid_samples": "min_valid_samples",
        "top_candidates": "top_candidates",
        "enrichment_alpha": "enrichment_alpha",
    }
    changes: dict[str, Any] = {}
    casters = {
        "fdr_threshold": float,
        "delta_psi_threshold": float,
        "min_support_reads": int,
        "min_valid_samples": int,
        "top_candidates": int,
        "enrichment_alpha": float,
    }
    for key, value in thresholds.items():
        field = mapping.get(str(key))
        if field is None or value in (None, ""):
            continue
        try:
            changes[field] = casters[field](value)  # type: ignore[operator]
        except (TypeError, ValueError):
            continue
    if not changes:
        return settings
    new_analysis = dataclasses.replace(analysis, **changes)
    return dataclasses.replace(settings, analysis=new_analysis)


def create_app() -> FastAPI:
    """Build the SpliceGAIP API application."""
    # Load .env file so API keys are available in environment variables
    from splicegaip.llm.envfile import load_env_values
    load_env_values()

    app = FastAPI(title="SpliceGAIP API", version=API_VERSION)
    settings, storage_warnings = load_prepared_settings()
    ensure_runtime_dirs(settings)

    # The built-in MCP tool server runs in-process so the AI assistant always
    # has a live tool provider, including in the packaged one-file build.
    try:
        from splicegaip.mcp.demo_server import ensure_demo_server

        demo_status = ensure_demo_server()
        if demo_status.get("running"):
            logger.info("Built-in MCP server listening on %s", demo_status.get("url"))
        else:
            logger.warning("Built-in MCP server unavailable: %s", demo_status.get("error"))
    except Exception as error:  # noqa: BLE001 - MCP must never block boot
        logger.warning("Built-in MCP server failed to start: %s", error)
    log_path = os.getenv("SPLICEGAIP_LOG_FILE") or (
        settings.paths.runtime_root / "logs" / "splicegaip.log"
    )
    configure_logging(log_path)
    configured_api_key = os.getenv("SPLICEGAIP_API_KEY", "").strip()
    try:
        configured_rate_limit = max(0, int(os.getenv("SPLICEGAIP_RATE_LIMIT", "0")))
    except ValueError:
        configured_rate_limit = 0
    rate_state: dict[str, tuple[float, int]] = {}
    rate_lock = threading.Lock()

    @app.get("/")
    def index() -> Any:
        """Serve the browser UI (what the desktop exe opens automatically)."""
        return render_web_ui(f"SpliceGAIP v{API_VERSION}")

    @app.get("/assets/opencc-cn2t.js", include_in_schema=False)
    def traditional_chinese_converter() -> FileResponse:
        """Serve the bundled, offline Chinese script converter."""
        converter = Path(__file__).resolve().parent.parent / "interface" / "opencc-cn2t.js"
        return FileResponse(converter, media_type="application/javascript")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(content=_FAVICON_SVG, media_type="image/svg+xml")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": API_VERSION, "llm_configured": settings.llm.configured}

    @app.middleware("http")
    async def request_boundary(request: Request, call_next: Any) -> Response:
        """Apply request correlation, baseline headers, and optional API auth."""
        request_id = new_request_id(request.headers.get("X-Request-ID"))
        token = set_request_id(request_id)
        started = time.perf_counter()
        response: Response
        try:
            protected = request.url.path.startswith("/api/") and request.url.path != (
                "/api/health"
            )
            rate_limited = False
            if configured_rate_limit and protected:
                client_id = request.client.host if request.client else "unknown"
                now = time.monotonic()
                with rate_lock:
                    window_start, count = rate_state.get(client_id, (now, 0))
                    if now - window_start >= 60:
                        window_start, count = now, 0
                    if count >= configured_rate_limit:
                        rate_limited = True
                        retry_after = max(1, int(60 - (now - window_start)) + 1)
                    else:
                        rate_state[client_id] = (window_start, count + 1)
            if rate_limited:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )
            elif configured_api_key and protected:
                supplied = request.headers.get("X-API-Key", "")
                authorization = request.headers.get("Authorization", "")
                if not supplied and authorization.lower().startswith("bearer "):
                    supplied = authorization[7:].strip()
                if not secrets.compare_digest(supplied, configured_api_key):
                    response = JSONResponse(
                        status_code=401,
                        content={"detail": "API authentication required"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    response = await call_next(request)
            else:
                response = await call_next(request)
        except Exception:
            logger.exception("request_failed", extra={"event": "request_failed"})
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            # The response is intentionally logged only after call_next returns;
            # rejected requests are still observable without logging credentials.
            if "response" in locals():
                logger.info(
                    "request_completed",
                    extra={
                        "event": "request_completed",
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
            reset_request_id(token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    def _fresh_settings() -> Any:
        """Reload settings so a key saved through /api/llm/config is live.

        ``settings`` captured above would otherwise keep the credentials the
        process started with, which makes "paste the key in the UI" look like
        it silently failed.
        """
        from splicegaip.config import load_settings

        try:
            return load_settings()
        except Exception:  # noqa: BLE001 - keep the boot-time settings
            return settings

    @app.get("/api/llm/status")
    def llm_status_endpoint() -> dict[str, Any]:
        """Is a model endpoint configured, and what may it enrich?"""
        from splicegaip.llm.enrich import llm_status
        from splicegaip.llm.envfile import env_config_payload

        payload = llm_status(_fresh_settings())
        payload["config"] = env_config_payload()
        return payload

    @app.post("/api/llm/config")
    def llm_config(payload: dict[str, Any]) -> dict[str, Any]:
        """Save model credentials into the local ``.env`` file.

        Accepts ``{"values": {...}}`` or the flat form (``{"MODEL_API_KEY":
        "sk-..."}``). A preset id may be merged in first with
        ``{"preset": "deepseek-flash"}``. Secrets never leave this machine and
        only a masked copy is returned.
        """
        from splicegaip.llm.envfile import PRESETS, write_env_values

        updates: dict[str, str] = {}
        preset = str(payload.get("preset", "")).strip()
        if preset:
            chosen = PRESETS.get(preset)
            if chosen is None:
                raise HTTPException(status_code=400, detail=f"unknown preset: {preset}")
            updates.update({k: v for k, v in chosen.items() if k != "label"})
        raw = payload.get("values")
        if isinstance(raw, dict):
            updates.update({str(key): str(value) for key, value in raw.items()})
        else:
            updates.update({
                str(key): str(value) for key, value in payload.items() if key not in ("preset", "values")
            })
        if not updates:
            raise HTTPException(status_code=400, detail="no configuration values supplied")
        try:
            path, changed = write_env_values(updates)
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"cannot write .env: {error}") from error
        from splicegaip.llm.enrich import llm_status
        from splicegaip.llm.envfile import env_config_payload

        return {
            "saved": True,
            "path": str(path),
            "updated": changed,
            "status": llm_status(_fresh_settings()),
            "config": env_config_payload(),
        }

    @app.post("/api/understand")
    def understand(payload: dict[str, Any]) -> dict[str, Any]:
        """Resolve a natural-language question into a structured intent.

        Model-based when an endpoint is configured, rule-based otherwise,
        so the UI can show the same panel in both modes.
        """
        query = str(payload.get("query", "")).strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")
        from splicegaip.llm.enrich import build_enhancer
        from splicegaip.llm.tasks import understand_query

        facts = payload.get("facts") if isinstance(payload.get("facts"), dict) else None
        try:
            from splicegaip.llm.enrich import build_enhancer

            enhancer = build_enhancer(_fresh_settings())
            result = understand_query(query, enhancer=enhancer, facts=facts)
            # Surface why the model path was skipped: without this the UI shows
            # a perfectly reasonable rule-based answer and the user cannot tell
            # that their key / endpoint is not actually working.
            if isinstance(result, dict) and result.get("source") != "llm" and enhancer.errors:
                result["llm_errors"] = enhancer.errors[-3:]
            return result
        except Exception as error:  # noqa: BLE001 - degrade to the rule baseline
            from splicegaip.llm.tasks import classify_query_fallback

            fallback = classify_query_fallback(query, error=str(error))
            fallback["llm_errors"] = [{"feature": "understand", "error": str(error)}]
            return fallback

    @app.get("/api/projects")
    def projects() -> dict[str, Any]:
        return {"projects": list_projects(settings)}

    @app.get("/api/status/{project_id}")
    def status(project_id: str) -> dict[str, Any]:
        payload = project_status(project_id, settings)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        return payload

    @app.post("/api/analyze")
    def analyze(payload: dict[str, Any]) -> dict[str, Any]:
        query = str(payload.get("query", "")).strip()
        input_dir = str(payload.get("input_dir", "")).strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")
        if not input_dir or not Path(input_dir).exists():
            raise HTTPException(status_code=400, detail=f"input_dir does not exist: {input_dir}")

        run_settings = _with_overrides(settings, payload.get("thresholds"))
        try:
            outcome = run_analysis(query, input_dir, settings=run_settings, project_name=str(payload.get("project_name") or "").strip()[:120])
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return JSONResponse(outcome.summary())

    def _ingest_input_dir(raw: str) -> Path:
        """Resolve an ingestion directory and keep model exposure local.

        The UI always uploads into the runtime directory; this guard stops a
        remote caller (when the API is exposed) from pointing the model-backed
        profiler at arbitrary files elsewhere on the machine.
        """
        value = str(raw or "").strip()
        if not value:
            raise HTTPException(status_code=400, detail="input_dir is required")
        path = Path(value).expanduser().resolve()
        if not path.is_dir():
            raise HTTPException(status_code=400, detail=f"input_dir does not exist: {path}")
        if os.getenv("SPLICEGAIP_INGEST_ALLOW_EXTERNAL", "").strip().lower() in {"1", "true", "yes"}:
            return path
        roots = [settings.paths.runtime_root.resolve(), Path.cwd().resolve()]
        if not any(path == root or root in path.parents for root in roots):
            raise HTTPException(
                status_code=400,
                detail="input_dir must be inside the runtime or working directory for ingestion",
            )
        return path

    @app.post("/api/ingest/preview")
    def ingest_preview(payload: dict[str, Any]) -> dict[str, Any]:
        """Profile messy input and propose a reviewed mapping (no files written)."""
        from splicegaip.data.ingestion import preview_ingestion

        directory = _ingest_input_dir(str(payload.get("input_dir", "")))
        try:
            return preview_ingestion(
                directory,
                settings=_fresh_settings(),
                use_llm=bool(payload.get("use_llm", True)),
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:  # noqa: BLE001 - surface a useful 500
            logger.exception("Ingestion preview failed")
            raise HTTPException(status_code=500, detail=f"Ingestion preview failed: {error}") from error

    @app.post("/api/ingest/apply")
    def ingest_apply(payload: dict[str, Any]) -> dict[str, Any]:
        """Convert files with a confirmed mapping into a standardized directory."""
        from splicegaip.data.ingestion import apply_ingestion

        directory = _ingest_input_dir(str(payload.get("input_dir", "")))
        mapping = payload.get("mapping")
        if not isinstance(mapping, dict) or not mapping:
            raise HTTPException(status_code=400, detail="mapping is required")
        try:
            return apply_ingestion(directory, mapping)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"Cannot write standardized data: {error}") from error
        except Exception as error:  # noqa: BLE001 - surface a useful 500
            logger.exception("Ingestion apply failed")
            raise HTTPException(status_code=500, detail=f"Ingestion apply failed: {error}") from error

    @app.post("/api/ingest/groups")
    def ingest_groups(payload: dict[str, Any]) -> dict[str, Any]:
        """Persist confirmed sample groups for an already recognized input."""
        from splicegaip.data.ingestion import apply_native_groups

        directory = _ingest_input_dir(str(payload.get("input_dir", "")))
        groups = payload.get("sample_groups")
        if not isinstance(groups, dict):
            raise HTTPException(status_code=400, detail="sample_groups is required")
        try:
            return apply_native_groups(directory, groups)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/upload")
    async def upload(files: list[UploadFile] = File(...)) -> dict[str, Any]:
        """Upload analysis input files into a new staging directory."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Received {len(files)} files in request")
        logger.info(f"Files type: {type(files)}")
        for idx, f in enumerate(files):
            logger.info(f"  File {idx}: {f.filename}, content_type={f.content_type}")
        
        if not files:
            logger.error("No files found in form data")
            raise HTTPException(status_code=400, detail="No files provided")
        
        try:
            staging = Path(tempfile.mkdtemp(prefix="splicegaip_upload_", dir=str(settings.paths.runtime_root)))
            logger.info(f"Created staging directory: {staging}")
            
            uploaded_files = []
            for idx, upload in enumerate(files):
                if not upload.filename:
                    logger.warning(f"File {idx} has no filename, skipping")
                    continue
                    
                destination = staging / Path(upload.filename).name
                logger.info(f"Saving file {idx+1}/{len(files)}: {upload.filename} ({upload.content_type}) -> {destination}")
                
                with destination.open("wb") as handle:
                    content = await upload.read()
                    handle.write(content)
                    logger.info(f"Saved {len(content)} bytes to {destination}")
                
                uploaded_files.append(upload.filename)
            
            logger.info(f"Upload complete: {len(uploaded_files)} files saved to {staging}")
            return {"upload_dir": str(staging), "files": uploaded_files}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") from e
    
    # Debug endpoint to test file upload
    @app.post("/api/upload-debug")
    async def upload_debug(request: Request):
        """Debug endpoint to inspect incoming request."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(
            "upload_debug_request",
            extra={
                "event": "upload_debug_request",
                "method": request.method,
                "content_type": request.headers.get("content-type", ""),
            },
        )
        
        try:
            form = await request.form()
            logger.info(f"Form keys: {list(form.keys())}")
            for key, value in form.multi_items():
                logger.info(f"  {key}: {type(value).__name__} - {getattr(value, 'filename', 'N/A')}")
            return {"form_keys": list(form.keys()), "success": True}
        except Exception as e:
            logger.error(f"Form parsing failed: {e}", exc_info=True)
            return {"error": str(e)}

    @app.get("/api/report/{project_id}")
    def report(project_id: str, format: str = "html") -> Any:
        payload = project_status(project_id, settings)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        for artifact in payload["artifacts"]:
            if artifact["kind"] == f"report:{format}" and Path(artifact["path"]).is_file():
                return FileResponse(artifact["path"])
        raise HTTPException(status_code=404, detail=f"No {format} report for project {project_id}")

    # ==================== MCP Integration Endpoints ====================

    @app.get("/api/mcp/servers")
    async def mcp_servers(refresh: bool = False) -> dict[str, Any]:
        """List configured MCP servers, connection state and tool schemas."""
        from splicegaip.mcp import get_mcp_client

        client = get_mcp_client()
        result: dict[str, Any] = {}

        for server_name, config in client.servers.items():
            if not config.enabled:
                result[server_name] = {
                    "status": "disabled",
                    "transport": config.transport,
                    "builtin": config.builtin,
                    "tools": [],
                }
                continue
            try:
                connected = (
                    await client.refresh(server_name)
                    if refresh
                    else await client.connect(server_name)
                )
                if connected:
                    tools = await client.list_tools(server_name)
                    result[server_name] = {
                        "status": "connected",
                        "transport": config.transport,
                        "via": client._connected_via.get(server_name),
                        "builtin": config.builtin,
                        "url": config.url,
                        "tools": [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "input_schema": tool.input_schema or {},
                            }
                            for tool in tools
                        ],
                    }
                else:
                    result[server_name] = {
                        "status": "disconnected",
                        "transport": config.transport,
                        "builtin": config.builtin,
                        "url": config.url,
                        "tools": [],
                    }
            except Exception as error:  # noqa: BLE001 - one bad server must not hide others
                result[server_name] = {
                    "status": "error",
                    "transport": config.transport,
                    "builtin": config.builtin,
                    "url": config.url,
                    "error": str(error),
                    "tools": [],
                }

        return {
            "servers": result,
            "config_path": str(client.config_path),
            "builtin_server": "splicegaip-builtin",
        }

    @app.post("/api/mcp/call")
    async def mcp_call_tool(payload: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool on a connected server."""
        from splicegaip.mcp import get_mcp_client

        server_name = str(payload.get("server_name", "")).strip()
        tool_name = str(payload.get("tool_name", "")).strip()
        arguments = payload.get("arguments", {})

        if not server_name or not tool_name:
            raise HTTPException(status_code=400, detail="server_name and tool_name are required")
        if arguments in (None, ""):
            arguments = {}
        if not isinstance(arguments, dict):
            raise HTTPException(status_code=400, detail="arguments must be a JSON object")

        client = get_mcp_client()
        if server_name not in client.servers:
            raise HTTPException(status_code=404, detail=f"unknown MCP server: {server_name}")
        result = await client.call_tool(server_name, tool_name, arguments)

        if "error" in result:
            return {"success": False, "error": result["error"], "raw": result.get("result")}

        return {"success": True, "result": result, "server": server_name, "tool": tool_name}

    @app.post("/api/mcp/agent")
    async def mcp_agent(payload: dict[str, Any]) -> dict[str, Any]:
        """Let the model pick one MCP tool for a natural-language request.

        The model only proposes ``{server, tool, arguments}``; validation and
        execution stay local. Without a model endpoint a deterministic router
        mirrors the same contract, so the demo never dead-ends.
        """
        import asyncio

        question = str(payload.get("question", "")).strip()
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        project_hint = str(payload.get("project_id", "")).strip()

        from splicegaip.mcp import get_mcp_client

        client = get_mcp_client()
        catalog: list[dict[str, Any]] = []
        for server_name, config in client.servers.items():
            if not config.enabled or not await client.connect(server_name):
                continue
            for tool in await client.list_tools(server_name):
                catalog.append(
                    {
                        "server": server_name,
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema or {},
                    }
                )
        if not catalog:
            raise HTTPException(status_code=503, detail="no MCP tools are available")

        project_ids = [
            str(item.get("project_id"))
            for item in list_projects(settings)[:10]
            if item.get("project_id")
        ]
        if project_hint not in project_ids:
            project_hint = ""

        def sanitise(candidate: Any) -> dict[str, Any] | None:
            if not isinstance(candidate, dict):
                return None
            server = str(candidate.get("server", "")).strip()
            tool_name = str(candidate.get("tool", "")).strip()
            arguments = candidate.get("arguments") or {}
            if not tool_name or not isinstance(arguments, dict):
                return None
            entry = next(
                (
                    item
                    for item in catalog
                    if item["server"] == server and item["name"] == tool_name
                ),
                None,
            )
            if entry is None:
                matches = [item for item in catalog if item["name"] == tool_name]
                if len(matches) != 1:
                    return None
                entry = matches[0]
                server = entry["server"]
            schema = entry.get("input_schema") or {}
            allowed = set((schema.get("properties") or {}).keys())
            arguments = {key: value for key, value in arguments.items() if key in allowed}
            if "project_id" in allowed:
                supplied = str(arguments.get("project_id", "")).strip()
                if supplied not in project_ids:
                    arguments["project_id"] = project_hint or (
                        project_ids[0] if project_ids else ""
                    )
                if not arguments["project_id"]:
                    arguments.pop("project_id", None)
            missing = set(schema.get("required") or []) - set(arguments)
            if missing:
                return None
            return {
                "server": server,
                "tool": tool_name,
                "arguments": arguments,
                "reason": str(candidate.get("reason", "")).strip()[:300],
            }

        def rule_plan() -> dict[str, Any]:
            def entry_for(name: str) -> dict[str, Any] | None:
                return next((item for item in catalog if item["name"] == name), None)

            project_id = project_hint or (project_ids[0] if project_ids else "")
            type_match = re.search(
                r"(?<![A-Za-z0-9])(SE|MXE|A5SS|A3SS|RI)(?![A-Za-z0-9])",
                question.upper(),
            )
            if type_match and entry_for("explain_event_type"):
                return {
                    "server": entry_for("explain_event_type")["server"],
                    "tool": "explain_event_type",
                    "arguments": {"event_type": type_match.group(1)},
                    "reason": "识别到剪接事件类型关键词",
                }
            numbers = re.findall(
                r"(?<![\w.])(0(?:\.\d+)?|1(?:\.0+)?)(?![\w.])", question
            )
            if len(numbers) >= 2 and entry_for("compute_delta_psi"):
                return {
                    "server": entry_for("compute_delta_psi")["server"],
                    "tool": "compute_delta_psi",
                    "arguments": {
                        "group1_psi": float(numbers[0]),
                        "group2_psi": float(numbers[1]),
                    },
                    "reason": "识别到两个 PSI 数值，计算 ΔPSI",
                }
            gene_match = re.search(
                r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,9})(?![A-Za-z0-9])", question
            )
            excluded = {
                "PSI", "FDR", "MCP", "RNA", "DNA", "CDNA", "PCR", "AI",
                "SE", "MXE", "RI", "A5SS", "A3SS",
            }
            if (
                gene_match
                and gene_match.group(1) not in excluded
                and entry_for("search_events")
                and project_id
            ):
                return {
                    "server": entry_for("search_events")["server"],
                    "tool": "search_events",
                    "arguments": {
                        "project_id": project_id,
                        "gene": gene_match.group(1),
                        "limit": 10,
                    },
                    "reason": "识别到基因符号，检索该基因的剪接事件",
                }
            if (
                "项目" in question
                and any(word in question for word in ("列表", "哪些", "多少"))
                and entry_for("list_projects")
            ):
                return {
                    "server": entry_for("list_projects")["server"],
                    "tool": "list_projects",
                    "arguments": {},
                    "reason": "询问项目列表",
                }
            if entry_for("project_summary") and project_id:
                return {
                    "server": entry_for("project_summary")["server"],
                    "tool": "project_summary",
                    "arguments": {"project_id": project_id},
                    "reason": "默认读取当前项目摘要",
                }
            if entry_for("list_projects"):
                return {
                    "server": entry_for("list_projects")["server"],
                    "tool": "list_projects",
                    "arguments": {},
                    "reason": "未指定项目，先列出可用项目",
                }
            first = catalog[0]
            return {
                "server": first["server"],
                "tool": first["name"],
                "arguments": {},
                "reason": "默认使用首个可用工具",
            }

        plan: dict[str, Any] | None = None
        source = "rule"
        llm_errors: list[Any] = []
        try:
            from splicegaip.llm.enrich import build_enhancer

            enhancer = build_enhancer(_fresh_settings())
            if enhancer.enabled and enhancer.has("plan"):
                system = (
                    "You route a user's request to exactly one MCP tool. "
                    "Return JSON only with keys: server, tool, arguments, reason. "
                    "Use only the provided servers/tools and their schema properties. "
                    "Never invent project IDs; pick one from projects if needed. "
                    "Prefer search_events for gene-level splicing questions, "
                    "project_summary for whole-project questions, and "
                    "explain_event_type for terminology questions."
                )
                user = json.dumps(
                    {
                        "question": question,
                        "current_project": project_hint or None,
                        "projects": project_ids,
                        "tools": [
                            {
                                "server": item["server"],
                                "tool": item["name"],
                                "description": item["description"],
                                "input_schema": item["input_schema"],
                            }
                            for item in catalog
                        ],
                    },
                    ensure_ascii=False,
                )
                candidate = await asyncio.to_thread(
                    enhancer.json,
                    system=system,
                    user=user,
                    feature="plan",
                    max_tokens=600,
                    timeout=40,
                )
                plan = sanitise(candidate)
                if plan is not None:
                    source = "llm"
                llm_errors = enhancer.errors[-3:]
        except Exception as error:  # noqa: BLE001 - fall back to deterministic routing
            llm_errors = [{"error": str(error)}]

        if plan is None:
            plan = rule_plan()

        started = time.perf_counter()
        result = await client.call_tool(plan["server"], plan["tool"], plan["arguments"])
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "success": "error" not in result,
            "error": result.get("error"),
            "source": source,
            "plan": plan,
            "result": result,
            "elapsed_ms": elapsed_ms,
            "llm_errors": llm_errors,
        }

    # ==================== Skills Endpoints ====================

    @app.get("/api/skills/list")
    def skills_list() -> dict[str, Any]:
        """List all available splicing-specific skills."""
        from splicegaip.skills import (
            GeneAnnotationSkill,
            LiteratureSearchSkill,
            PathwayEnrichmentSkill,
            SpliceInterpretationSkill,
        )

        skills = [
            GeneAnnotationSkill(),
            LiteratureSearchSkill(),
            PathwayEnrichmentSkill(),
            SpliceInterpretationSkill(),
        ]

        return {
            "skills": [
                {
                    "name": skill.name,
                    "description": skill.description,
                    "input_schema": skill.input_schema,
                }
                for skill in skills
            ]
        }

    @app.post("/api/skills/execute")
    async def skills_execute(payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a splicing-specific skill.

        Expected payload:
        {
            "skill_name": "gene_annotation",
            "parameters": {
                "gene_symbol": "BRCA1",
                "include_splicing": true
            }
        }
        """
        skill_name = payload.get("skill_name")
        parameters = payload.get("parameters", {})

        if not skill_name:
            raise HTTPException(status_code=400, detail="skill_name is required")

        # Import and instantiate the requested skill
        skill_map = {
            "gene_annotation": "GeneAnnotationSkill",
            "literature_search": "LiteratureSearchSkill",
            "pathway_enrichment": "PathwayEnrichmentSkill",
            "splice_interpretation": "SpliceInterpretationSkill",
        }

        skill_class_name = skill_map.get(skill_name)
        if not skill_class_name:
            raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_name}")

        # Dynamic import to avoid circular dependencies
        import importlib

        module = importlib.import_module("splicegaip.skills")
        skill_class = getattr(module, skill_class_name)
        skill = skill_class()

        # Validate input
        is_valid, error_msg = skill.validate_input(**parameters)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Execute the skill
        result = await skill.execute(**parameters)

        return result.to_dict()

    @app.get("/api/figure/{project_id}/{figure_name}")
    def figure(project_id: str, figure_name: str) -> Any:
        safe_name = Path(figure_name).stem
        for extension in (".png", ".svg"):
            candidate = settings.paths.runtime_root / "projects" / project_id / "figures" / f"{safe_name}{extension}"
            if candidate.is_file():
                return FileResponse(candidate)
        payload = project_status(project_id, settings)
        if payload is not None:
            for artifact in payload["artifacts"]:
                if artifact["kind"] == f"figure:{safe_name}" and Path(artifact["path"]).is_file():
                    return FileResponse(artifact["path"])
            if safe_name in extra_figures.ON_DEMAND_FIGURES:
                target_dir = settings.paths.runtime_root / "projects" / project_id / "figures"
                try:
                    generated = _build_on_demand_figure(safe_name, payload, target_dir)
                    if generated is not None and generated.is_file():
                        return FileResponse(generated)
                except Exception as exc:  # noqa: BLE001 - never crash the endpoint
                    logger.warning("on-demand figure %s failed: %s", safe_name, exc)
        raise HTTPException(status_code=404, detail=f"Figure {figure_name} not found")

    return app


def _build_on_demand_figure(name: str, payload: dict[str, Any], target_dir: Path) -> Path | None:
    """Generate a lazy figure from persisted project state."""
    candidates = payload.get("candidates") or []
    samples = payload.get("samples") or []
    if name == "dpsi_waterfall":
        return extra_figures.plot_dpsi_waterfall(candidates, target_dir)
    if name == "dpsi_ecdf":
        return extra_figures.plot_dpsi_ecdf(candidates, target_dir)
    if name == "fdr_scree":
        return extra_figures.plot_fdr_scree(candidates, target_dir)
    if name == "event_significance":
        return extra_figures.plot_event_significance(candidates, target_dir)
    if name == "score_components":
        return extra_figures.plot_score_components(candidates, target_dir)
    if name == "sample_composition":
        return extra_figures.plot_sample_composition(samples, target_dir)
    if name == "event_schematic":
        return extra_figures.plot_event_schematic(target_dir)
    return None


app = create_app()
