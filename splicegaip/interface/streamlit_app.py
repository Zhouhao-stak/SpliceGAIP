"""Streamlit dashboard.

Pages: run an analysis (upload + goal), inspect results (candidates,
figures, enrichment), and download the generated report.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

# Apply professional minimalist theme
try:
    from splicegaip.ui.theme_professional import apply_professional_theme
    apply_professional_theme()
except ImportError:
    pass  # Fallback to default Streamlit styling

from splicegaip.config import load_prepared_settings
from splicegaip.pipeline import list_projects, project_status, resume_analysis, run_analysis

_STATUS_COLOR = {"ok": "#1a7f37", "failed": "#cf222e", "skipped": "#6e7781"}
_STATUS_ICON = {"ok": "✅", "failed": "❌", "skipped": "⏭️"}
_VERDICT_COLOR = {"rejected": "#cf222e", "retained": "#1a7f37", "inconclusive": "#9a6700"}


def _render_timeline(steps: list[dict]) -> None:
    """Vertical decision timeline with colour-coded step status."""
    if not steps:
        st.caption("no decision steps recorded")
        return
    html_rows = []
    for step in steps:
        color = _STATUS_COLOR.get(step["status"], "#6e7781")
        icon = _STATUS_ICON.get(step["status"], "•")
        html_rows.append(
            f"<div style='margin:2px 0;font-size:13px'>"
            f"<span style='color:{color};font-weight:600'>{icon} {step['index'] + 1}. "
            f"{step['action']}</span> "
            f"<span style='background:#eaeef2;border-radius:4px;padding:0 5px;font-size:11px'>"
            f"{step['source']}</span> — {step['rationale'][:90]}</div>"
        )
    st.markdown("".join(html_rows), unsafe_allow_html=True)


def _render_hypotheses(items: list[dict]) -> None:
    """Self-check results with verdict colouring."""
    html_rows = []
    for item in items:
        color = _VERDICT_COLOR.get(item["verdict"], "#6e7781")
        html_rows.append(
            f"<div style='font-size:13px;margin:2px 0'><b>{item['code']}</b> "
            f"<span style='color:{color};font-weight:600'>{item['verdict']}</span> "
            f"(p={item['p_value']}, q={item['fdr']}, n={item['n']}) — {item['effect'][:70]}</div>"
        )
    st.markdown("".join(html_rows), unsafe_allow_html=True)


@st.cache_resource
def _load_settings():
    """Load settings once and cache them across reruns."""
    return load_prepared_settings()


def main() -> None:
    st.set_page_config(page_title="SpliceGAIP", page_icon="🧬", layout="wide")
    settings, storage_warnings = _load_settings()
    mode = "LLM" if settings.llm.configured else "deterministic (offline policy)"
    st.title("🧬 SpliceGAIP")
    st.caption(
        f"AI-driven Alternative Splicing Analysis Platform · agent mode: {mode}"
    )

    page = st.sidebar.radio("Navigate", ["Run analysis", "Projects", "Results"], index=0)

    if page == "Run analysis":
        _render_run_page(settings)
    elif page == "Projects":
        _render_projects_page(settings)
    else:
        _render_results_page(settings)


def _render_run_page(settings) -> None:
    st.header("Run analysis")
    st.markdown(
        "Upload your analysis input (rMATS JC tables, SUPPA2 `.psi.tsv` files, a "
        "standardized `AS_event_master.tsv`, or a differential-splicing CSV set "
        "such as `differential_splicing_results.csv` + `psi_matrix.csv`; optionally "
        "`sample_metadata.tsv`/`.csv`, `gene_annotation.tsv`, `differential_expression.tsv`)."
    )
    uploaded = st.file_uploader(
        "Input files",
        accept_multiple_files=True,
        type=["tsv", "txt", "csv"],
    )
    query = st.text_area(
        "Analysis goal (natural language)",
        value="分析RNA剪接变化：找出两组之间差异显著的剪接事件并排序候选基因",
        height=80,
    )
    if st.button("Run analysis", type="primary"):
        if not uploaded:
            st.warning("Please upload at least one input file.")
            return
        staging = Path(tempfile.mkdtemp(prefix="splicegaip_ui_"))
        for upload in uploaded:
            (staging / Path(upload.name).name).write_bytes(upload.getvalue())
        with st.spinner("Running the multi-agent analysis..."):
            try:
                outcome = run_analysis(query, staging, settings=settings)
            except ValueError as error:
                st.error(str(error))
                return
        st.success(f"Analysis complete (project {outcome.project_id}, mode: {outcome.team.mode}).")
        st.session_state["last_project_id"] = outcome.project_id
        _render_outcome(outcome)


def _render_outcome(outcome) -> None:
    summary = outcome.summary()
    st.subheader("Run summary")
    st.json(
        {
            "project_id": summary["project_id"],
            "mode": summary["mode"],
            "stopped_reason": summary["stopped_reason"],
            "tool_calls": summary["tool_calls"],
            "figures": summary["figures"],
        }
    )
    agent = summary.get("agent") or {}
    if agent:
        st.subheader("Agent decision trace")
        st.caption(
            f"goal: {agent['goal'].get('description', '')} · "
            f"satisfied={agent['goal_satisfied']} · "
            f"params={agent['params']}"
        )
        _render_timeline(agent["steps"])
        for issue in agent["issues"]:
            st.warning(f"{issue['severity']}: {issue['code']} — {issue['message']}")
        for item in agent["accepted_limitations"]:
            st.info(f"accepted limitation: {item['code']} — {item['reason']}")
        if agent.get("skills"):
            st.caption(
                f"external skills: enabled={agent['skills'].get('enabled')} · "
                f"{agent['skills'].get('used')}/{agent['skills'].get('budget')} calls used"
            )
        if agent.get("hypotheses"):
            st.subheader("Hypothesis tests (agent self-check)")
            _render_hypotheses(agent["hypotheses"])

    st.subheader("Top candidates")
    st.table(
        [
            {
                "rank": index,
                "gene": item["gene_symbol"] or item["gene_id"],
                "event": item["event_type"],
                "delta_PSI": item["delta_PSI"],
                "FDR": item["FDR"],
                "score": item["score"],
            }
            for index, item in enumerate(summary["top_candidates"], start=1)
        ]
    )
    figures_dir = outcome.output_dir / "figures"
    if figures_dir.is_dir():
        pngs = sorted(figures_dir.glob("*.png"))
        if pngs:
            st.subheader("Figures")
            for png in pngs:
                st.image(str(png), caption=png.stem, width="stretch")
    st.subheader("Report")
    for kind, path in outcome.report_paths.items():
        with Path(path).open("rb") as handle:
            st.download_button(
                f"Download {kind.upper()} report",
                data=handle.read(),
                file_name=Path(path).name,
                key=f"{outcome.project_id}-{kind}",
            )


def _render_projects_page(settings) -> None:
    st.header("Projects")
    projects = list_projects(settings)
    
    # Always show a table for UI validation
    import pandas as pd
    
    if projects:
        df = pd.DataFrame([
            {
                "project_id": project["project_id"],
                "name": project["name"],
                "query": str(project.get("query", ""))[:60],
                "created_at": project["created_at"],
            }
            for project in projects
        ])
        st.table(df)
    else:
        # Show empty table with column headers
        df = pd.DataFrame(columns=["project_id", "name", "query", "created_at"])
        st.table(df)
        st.info("No projects yet. Run an analysis first.")


def _render_results_page(settings) -> None:
    st.header("Results")
    project_id = st.text_input("Project id", value=st.session_state.get("last_project_id", ""))
    if not project_id:
        st.info("Enter a project id (see the Projects page).")
        return
    payload = project_status(project_id, settings)
    if payload is None:
        st.warning(f"Project {project_id} not found.")
        return
    # Workflow log - always show table even if empty
    st.subheader("Workflow log")
    logs = payload.get("logs", [])
    if logs:
        st.table(
            [
                {
                    "agent": entry["agent"],
                    "action": entry["action"],
                    "status": entry["status"],
                    "created_at": entry["created_at"],
                }
                for entry in logs
            ]
        )
    else:
        st.caption("No workflow logs recorded.")
    
    # Candidates table
    st.subheader("Candidates")
    candidates = payload.get("candidates", [])
    if candidates:
        st.table(
            [
                {
                    "rank": item["rank"],
                    "gene": item["gene_symbol"] or item["gene_id"],
                    "event": item["event_type"],
                    "delta_PSI": item["delta_psi"],
                    "FDR": item["fdr"],
                    "score": item["score"],
                }
                for item in candidates
            ]
        )
    else:
        st.caption("No candidates found.")
    
    # Figures - try multiple locations and formats
    figures_dir = settings.paths.runtime_root / "projects" / project_id / "figures"
    if not figures_dir.is_dir():
        # Fallback: check output_dir directly
        figures_dir = settings.paths.runtime_root / "projects" / project_id
    
    pngs = []
    if figures_dir.is_dir():
        pngs = sorted(figures_dir.glob("*.png"))
        if not pngs:
            # Try JPEG as fallback
            pngs = sorted(figures_dir.glob("*.jpg")) + sorted(figures_dir.glob("*.jpeg"))
    
    if pngs:
        st.subheader(f"Figures ({len(pngs)} images)")
        for png in pngs:
            st.image(str(png), caption=png.stem, use_container_width=True)
    else:
        st.caption("No figures available.")
    
    # Download buttons - ensure at least HTML and PDF are offered
    artifacts = payload.get("artifacts", [])
    download_buttons_added = 0
    
    # First, try to find report files from artifacts
    for artifact in artifacts:
        if artifact["kind"].startswith("report:") and Path(artifact["path"]).is_file():
            with Path(artifact["path"]).open("rb") as handle:
                fmt = artifact['kind'].split(':')[1].upper()
                import time
                safe_key = f"results_download_{fmt}_{project_id}_{int(time.time()*1000)}"
                st.download_button(
                    f"Download {fmt} report",
                    data=handle.read(),
                    file_name=Path(artifact["path"]).name,
                    key=safe_key,
                )
                download_buttons_added += 1
    
    # Fallback: look for report files directly in project directory
    project_dir = settings.paths.runtime_root / "projects" / project_id
    if download_buttons_added == 0:
        # Look for HTML report
        html_report = project_dir / "report.html"
        if html_report.is_file():
            with html_report.open("rb") as handle:
                import time
                st.download_button(
                    "Download HTML report",
                    data=handle.read(),
                    file_name="report.html",
                    key=f"results_html_{project_id}_{int(time.time()*1000)}",
                )
                download_buttons_added += 1
        
        # Look for PDF report
        pdf_report = project_dir / "report.pdf"
        if pdf_report.is_file():
            with pdf_report.open("rb") as handle:
                import time
                st.download_button(
                    "Download PDF report",
                    data=handle.read(),
                    file_name="report.pdf",
                    key=f"results_pdf_{project_id}_{int(time.time()*1000)}",
                )
                download_buttons_added += 1
    
    if download_buttons_added == 0:
        st.caption("No reports available for download.")


if __name__ == "__main__":
    main()
