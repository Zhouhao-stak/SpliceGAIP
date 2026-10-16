"""FastAPI application: upload / analyze / status / report."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from splicegaip.analysis import extra_figures
from splicegaip.config import ensure_runtime_dirs, load_prepared_settings
from splicegaip.interface.web_ui import render as render_web_ui
from splicegaip.pipeline import list_projects, project_status, run_analysis

API_VERSION = "0.1.0"

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

    @app.get("/")
    def index() -> Any:
        """Serve the browser UI (what the desktop exe opens automatically)."""
        return render_web_ui(f"SpliceGAIP v{API_VERSION}")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(content=_FAVICON_SVG, media_type="image/svg+xml")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": API_VERSION, "llm_configured": settings.llm.configured}

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
            outcome = run_analysis(query, input_dir, settings=run_settings)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return JSONResponse(outcome.summary())

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
        
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request content-type: {request.headers.get('content-type')}")
        
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
    async def mcp_list_servers() -> dict[str, Any]:
        """List all configured MCP servers and their available tools."""
        from splicegaip.mcp import get_mcp_client

        client = get_mcp_client()
        result = {}

        for server_name in client.servers:
            connected = await client.connect(server_name)
            if connected:
                tools = await client.list_tools(server_name)
                result[server_name] = {
                    "status": "connected",
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                        }
                        for tool in tools
                    ],
                }
            else:
                result[server_name] = {"status": "disconnected"}

        return {"servers": result}

    @app.post("/api/mcp/call")
    async def mcp_call_tool(payload: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool.

        Expected payload:
        {
            "server_name": "browser-use",
            "tool_name": "navigate_page",
            "arguments": {"url": "https://example.com"}
        }
        """
        from splicegaip.mcp import get_mcp_client

        server_name = payload.get("server_name")
        tool_name = payload.get("tool_name")
        arguments = payload.get("arguments", {})

        if not server_name or not tool_name:
            raise HTTPException(status_code=400, detail="server_name and tool_name are required")

        client = get_mcp_client()
        result = await client.call_tool(server_name, tool_name, arguments)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        return {"success": True, "result": result}

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
