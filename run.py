#!/usr/bin/env python3
"""SpliceGAIP command line interface.

Examples
--------
Run a full analysis::

    python run.py analyze --input examples/demo_rmats --query "分析RNA剪接变化"

List projects::

    python run.py projects

Show a project's workflow log::

    python run.py status --project-id SPN-XXXXXXXX

Serve the API / dashboard::

    python run.py serve --api --port 8800
    python run.py serve --ui --port 8501
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

# Fix Windows console encoding for Chinese characters
if sys.platform == "win32":
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
    except (AttributeError, LookupError):
        pass  # Fallback: keep default encoding

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _cmd_analyze(args: argparse.Namespace) -> int:
    from splicegaip.config import load_prepared_settings, load_settings
    from splicegaip.llm.client import describe_llm_mode
    from splicegaip.pipeline import run_analysis

    settings, _warnings = load_prepared_settings(args.config)
    agent_block = settings.agent
    if args.agent_mode:
        agent_block = dataclasses.replace(agent_block, mode=args.agent_mode)
    if args.autonomy:
        agent_block = dataclasses.replace(agent_block, autonomy=args.autonomy)
    if args.skills:
        agent_block = dataclasses.replace(
            agent_block,
            skills=dataclasses.replace(agent_block.skills, enabled=args.skills == "on"),
        )
    settings = dataclasses.replace(settings, agent=agent_block)
    print(f"[splicegaip] mode: {describe_llm_mode(settings)}")
    print(f"[splicegaip] engine: {'autonomous agent' if settings.agent.agentic else 'scripted team'}")
    print(
        f"[splicegaip] autonomy: {settings.agent.autonomy} "
        f"| external skills: {'on' if settings.agent.skills.enabled else 'off'} "
        f"| hypothesis tests: {'on' if settings.agent.hypothesis_testing else 'off'}"
    )
    print(f"[splicegaip] query: {args.query}")
    outcome = run_analysis(args.query, args.input, settings=settings, project_id=args.project_id)
    summary = outcome.summary()
    print(f"[splicegaip] project: {summary['project_id']}")
    print(f"[splicegaip] dataset: {json.dumps(summary['dataset'], ensure_ascii=False)}")
    print(f"[splicegaip] validation: {json.dumps(summary['validation'], ensure_ascii=False)}")
    print(f"[splicegaip] team: mode={summary['mode']} reason={summary['stopped_reason']} tool_calls={summary['tool_calls']}")
    print(f"[splicegaip] top candidates:")
    for index, candidate in enumerate(summary["top_candidates"], start=1):
        gene = candidate["gene_symbol"] or candidate["gene_id"]
        print(
            f"  {index:>2}. {gene:<12} {candidate['event_type']:<5} "
            f"dPSI={candidate['delta_PSI']} FDR={candidate['FDR']} score={candidate['score']}"
        )
    if summary["enriched_terms"]:
        print(f"[splicegaip] enriched terms: {', '.join(summary['enriched_terms'])}")
    agent = summary.get("agent") or {}
    if agent:
        print(
            f"[splicegaip] agent: goal_satisfied={agent['goal_satisfied']} "
            f"steps={len(agent['steps'])} issues={len(agent['issues'])} "
            f"params={json.dumps(agent['params'], ensure_ascii=False)}"
        )
        for step in agent["steps"]:
            print(
                f"  {step['index'] + 1:>2}. [{step['source']:<11}] {step['action']:<28} "
                f"{step['status']:<7} {step['rationale'][:70]}"
            )
        for issue in agent["issues"]:
            print(f"  ! {issue['severity']:<7} {issue['code']}: {issue['message'][:90]}")
    print(f"[splicegaip] figures: {', '.join(summary['figures'])}")
    print(f"[splicegaip] report: {json.dumps(summary['report_paths'], ensure_ascii=False)}")
    print(f"[splicegaip] output dir: {summary['output_dir']}")
    return 0


def _cmd_followup(args: argparse.Namespace) -> int:
    from splicegaip.config import (
        AgentSettings,
        load_prepared_settings,
        SkillSettings,
    )
    from splicegaip.pipeline import resume_analysis

    settings, _warnings = load_prepared_settings(args.config)
    agent_block: AgentSettings = settings.agent
    if args.autonomy:
        agent_block = dataclasses.replace(agent_block, autonomy=args.autonomy)
    if args.skills:
        agent_block = dataclasses.replace(
            agent_block,
            skills=SkillSettings(
                enabled=args.skills == "on",
                max_calls=agent_block.skills.max_calls,
                timeout=agent_block.skills.timeout,
            ),
        )
    settings = dataclasses.replace(settings, agent=agent_block)
    print(f"[splicegaip] resume: {args.project_id}")
    print(f"[splicegaip] autonomy: {settings.agent.autonomy} | skills: {'on' if settings.agent.skills.enabled else 'off'}")
    print(f"[splicegaip] query: {args.query}")
    try:
        outcome = resume_analysis(args.project_id, args.query, settings=settings)
    except ValueError as error:
        print(f"[splicegaip] error: {error}")
        return 1
    summary = outcome.summary()
    agent = summary.get("agent") or {}
    print(f"[splicegaip] resumed: mode={summary['mode']} reason={summary['stopped_reason']}")
    if agent:
        print(
            f"[splicegaip] agent: goal_satisfied={agent['goal_satisfied']} "
            f"steps={len(agent['steps'])} params={json.dumps(agent['params'], ensure_ascii=False)}"
        )
        for step in agent["steps"]:
            print(
                f"  {step['index'] + 1:>2}. [{step['source']:<11}] {step['action']:<28} "
                f"{step['status']:<7} {step['rationale'][:70]}"
            )
    print(f"[splicegaip] report: {json.dumps(summary['report_paths'], ensure_ascii=False)}")
    print(f"[splicegaip] output dir: {summary['output_dir']}")
    return 0


def _cmd_projects(args: argparse.Namespace) -> int:
    from splicegaip.config import load_prepared_settings, load_settings
    from splicegaip.pipeline import list_projects

    settings, _warnings = load_prepared_settings(args.config)
    projects = list_projects(settings)
    if not projects:
        print("No projects yet.")
        return 0
    for project in projects:
        print(f"{project['project_id']}  {project['created_at']}  {project['name']}  {project['query'][:60]}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    from splicegaip.config import load_prepared_settings, load_settings
    from splicegaip.pipeline import project_status

    settings, _warnings = load_prepared_settings(args.config)
    payload = project_status(args.project_id, settings)
    if payload is None:
        print(f"Project {args.project_id} not found.")
        return 1
    for entry in payload["logs"]:
        print(f"{entry['created_at']}  [{entry['agent']}] {entry['action']} -> {entry['status']}")
        if entry["detail"]:
            print(f"    {entry['detail'][:200]}")
    for artifact in payload["artifacts"]:
        print(f"artifact: {artifact['kind']} -> {artifact['path']}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import threading
    
    def start_api():
        import uvicorn
        from splicegaip.api.app import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port)
    
    def start_ui():
        import subprocess
        ui_path = Path(__file__).resolve().parent / "splicegaip" / "interface" / "streamlit_app.py"
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(ui_path), "--server.port", "8501", "--server.address", "0.0.0.0"]
        )
    
    threads = []
    if args.api:
        api_thread = threading.Thread(target=start_api, daemon=True)
        api_thread.start()
        threads.append(api_thread)
        print(f"API server starting on http://{args.host}:{args.port}")
    
    if args.ui:
        ui_thread = threading.Thread(target=start_ui, daemon=True)
        ui_thread.start()
        threads.append(ui_thread)
        print("Streamlit UI starting on http://0.0.0.0:8501")
    
    if not threads:
        print("Nothing to serve: pass --api or --ui.")
        return 1
    
    # Keep main thread alive
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="splicegaip", description="SpliceGAIP CLI")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Run a full analysis")
    analyze.add_argument("--input", required=True, help="Input file or directory")
    analyze.add_argument("--query", required=True, help="Natural-language analysis goal")
    analyze.add_argument("--project-id", default=None, help="Reuse a project id")
    analyze.add_argument(
        "--agent-mode",
        choices=("agentic", "scripted"),
        default=None,
        help="agentic = autonomous self-deciding loop (default); scripted = legacy fixed flow",
    )
    analyze.add_argument(
        "--autonomy",
        choices=("auto", "assisted"),
        default=None,
        help="auto = the agent decides alone; assisted = confirm risky decisions (network calls, threshold relaxation)",
    )
    analyze.add_argument(
        "--skills",
        choices=("on", "off"),
        default=None,
        help="enable/disable the external knowledge skills (MyGene / PubMed / Enrichr / splice interpretation)",
    )
    analyze.set_defaults(func=_cmd_analyze)

    followup = subparsers.add_parser(
        "followup", help="Resume a project with a follow-up query (multi-turn analysis)"
    )
    followup.add_argument("--project-id", required=True, help="An existing project id to continue")
    followup.add_argument("--query", required=True, help="Follow-up goal, e.g. 'zoom into TP53' or 'only SE events'")
    followup.add_argument(
        "--autonomy",
        choices=("auto", "assisted"),
        default=None,
        help="auto = the agent decides alone; assisted = confirm risky decisions",
    )
    followup.add_argument(
        "--skills",
        choices=("on", "off"),
        default=None,
        help="enable/disable the external knowledge skills",
    )
    followup.set_defaults(func=_cmd_followup)

    projects = subparsers.add_parser("projects", help="List projects")
    projects.set_defaults(func=_cmd_projects)

    status = subparsers.add_parser("status", help="Show a project's workflow log")
    status.add_argument("--project-id", required=True)
    status.set_defaults(func=_cmd_status)

    serve = subparsers.add_parser("serve", help="Serve the API or the dashboard")
    serve.add_argument("--api", action="store_true", help="Serve the FastAPI application")
    serve.add_argument("--ui", action="store_true", help="Serve the Streamlit dashboard")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8800)
    serve.set_defaults(func=_cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
