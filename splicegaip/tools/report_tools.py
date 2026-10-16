"""Report tool available to the Interpreter agent."""

from __future__ import annotations

from splicegaip.report.generator import ReportGenerator
from splicegaip.tools.context import RunContext


def generate_report(context: RunContext, output_dir: str | None = None) -> str:
    """Generate the scientific report (HTML and, if possible, PDF).

    Structure: Summary / Methods / Results / Figures / Biological
    Interpretation / Limitations / References.
    """
    directory = output_dir or str(context.output_dir)
    generator = ReportGenerator(context)
    paths = generator.generate(directory, formats=context.settings.report_formats)
    context.report_paths = paths
    for kind, path in paths.items():
        context.memory.save_artifact(context.project_id, f"report:{kind}", str(path))
    listing = ", ".join(f"{kind} -> {path}" for kind, path in paths.items())
    message = f"Generated report in {listing}."
    context.log("bio_interpreter", "generate_report", "ok", message)
    return message
