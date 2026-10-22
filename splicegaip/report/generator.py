"""Scientific report generator.

Produces a publication-style report with the sections required by the
SpliceGAIP design:

1. Summary  2. Methods  3. Results  4. Figures
5. Biological Interpretation  6. Limitations  7. References

HTML is the primary, self-contained deliverable (figures embedded as
base64 PNG). PDF is generated with reportlab when available.
"""

from __future__ import annotations

import base64
import html
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from splicegaip.tools.context import RunContext

REPORT_VERSION = "SpliceGAIP 0.1.0"


def _fmt(value: Any, digits: int = 3, na: str = "NA") -> str:
    if value is None:
        return na
    if isinstance(value, float):
        return f"{value:.{digits}g}" if abs(value) < 1 else f"{value:.{digits}f}"
    return str(value)


def build_interpretation(context: RunContext) -> str:
    """Deterministic, evidence-grounded interpretation text.

    Every statement is derived from computed results or from collected
    literature records; nothing is invented. This text is the factual
    backbone of the report and the offline Interpreter output.
    """
    dataset = context.dataset
    events = dataset.events
    significant = context.significant_events
    candidates = context.candidates
    evidence = context.evidence
    groups = dataset.groups
    group_labels = sorted(groups)
    control = group_labels[0] if group_labels else "group1"
    experiment = group_labels[-1] if len(group_labels) > 1 else "group2"

    lines: list[str] = []
    total = len(events)
    sig_count = len(significant)
    lines.append(
        f"The analysis processed {total} alternative splicing events "
        f"({', '.join(f'{key}={value}' for key, value in _event_type_counts(events).items())}) "
        f"from {len(dataset.samples)} samples comparing {control} versus {experiment}."
    )
    if context.filter_report is not None:
        report = context.filter_report
        lines.append(
            f"Applying the significance gates (FDR < {report.fdr_threshold}, "
            f"|delta PSI| > {report.delta_psi_threshold}) with quality controls retained "
            f"{sig_count} events ({_percent(sig_count, total)} of all events)."
        )
    else:
        lines.append(f"{sig_count} events passed the configured significance gates.")

    if candidates:
        top = candidates[:5]
        gene_names = [item.gene_symbol or item.gene_id for item in top]
        lines.append(
            "The highest-ranked candidate events involve "
            + ", ".join(gene_names)
            + ", selected by the composite score (0.4 statistical significance, "
            "0.3 effect size, 0.2 biological relevance, 0.1 literature evidence)."
        )
        strongest = max(top, key=lambda item: abs(item.delta_psi or 0.0))
        direction = "increased" if (strongest.delta_psi or 0) > 0 else "decreased"
        lines.append(
            f"The strongest effect was observed for {strongest.gene_symbol or strongest.gene_id} "
            f"({strongest.event_type}), where exon inclusion {direction} by "
            f"{_fmt(abs(strongest.delta_psi or 0.0))} PSI units "
            f"(delta PSI = {_fmt(strongest.delta_psi)}, FDR = {_fmt(strongest.fdr)})."
        )

    if context.enrichment:
        top_terms = context.enrichment[:3]
        lines.append(
            "Functional enrichment of candidate genes highlighted "
            + "; ".join(f"{item.term} ({item.gene_count} genes, {item.fold_enrichment}x enrichment)" for item in top_terms)
            + "."
        )

    covered = [gene for gene, entries in evidence.items() if entries]
    if covered:
        lines.append(
            f"Literature evidence was retrieved for {len(covered)} of the top candidate genes; "
            "reported associations are traceable to their sources and remain hypotheses until "
            "experimentally validated."
        )
    if not covered:
        lines.append(
            "No literature records were available for the candidate genes; the interpretation "
            "is therefore limited to the statistical evidence."
        )
    return "\n\n".join(lines)


def _event_type_counts(events: Sequence[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1
    return counts


def _percent(part: int, whole: int) -> str:
    return f"{100.0 * part / whole:.1f}%" if whole else "0%"


@dataclass(frozen=True)
class ReportGenerator:
    """Render the analysis report from a run context."""

    context: RunContext

    # -- HTML -------------------------------------------------------------
    def render_html(self) -> str:
        context = self.context
        dataset = context.dataset
        groups = dataset.groups
        group_labels = sorted(groups)
        control = group_labels[0] if group_labels else "group1"
        experiment = group_labels[-1] if len(group_labels) > 1 else "group2"
        interpretation = build_interpretation(context)
        limitations = self._limitations()
        references = self._references()

        candidate_rows = "".join(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(str(item.gene_symbol or item.gene_id))}</td>"
            f"<td>{html.escape(item.event_type)}</td>"
            f"<td>{_fmt(item.delta_psi)}</td>"
            f"<td>{_fmt(item.fdr)}</td>"
            f"<td>{item.score:.3f}</td>"
            "</tr>"
            for index, item in enumerate(context.candidates[:20], start=1)
        )
        enrichment_rows = "".join(
            "<tr>"
            f"<td>{html.escape(item.term)}</td>"
            f"<td>{html.escape(item.ontology)}</td>"
            f"<td>{item.gene_count}</td>"
            f"<td>{item.fold_enrichment}</td>"
            f"<td>{_fmt(item.fdr)}</td>"
            "</tr>"
            for item in context.enrichment[:20]
        )
        figure_blocks = "".join(
            f"<figure><img src=\"data:image/png;base64,{self._embed(figure.png_path)}\" "
            f"alt=\"{html.escape(figure.title)}\"/>"
            f"<figcaption><b>{html.escape(figure.title)}.</b> {html.escape(figure.caption)}</figcaption></figure>"
            for figure in context.figures
        )
        evidence_items = "".join(
            f"<li><b>{html.escape(gene)}</b>: {html.escape(entries[0].text)} "
            f"<i>({html.escape(entries[0].source)})</i></li>"
            for gene, entries in list(context.evidence.items())[:15]
            if entries
        )
        reference_items = "".join(f"<li>{html.escape(reference)}</li>" for reference in references)
        limitation_items = "".join(f"<li>{html.escape(item)}</li>" for item in limitations)
        summary_stats = self._summary_stats()
        ai_narrative = self._ai_narrative_html()
        ai_gene_notes = self._ai_gene_notes_html()
        ai_evidence_summary = self._ai_evidence_summary_html()
        ai_hypotheses = self._ai_hypotheses_html()
        ai_critique = self._ai_critique_html()
        ai_model = self._ai_model_html()
        provenance_number = "9" if ai_hypotheses else "8"
        hypothesis_tests = self._hypothesis_html()
        external_findings = self._external_html()
        recurrence_section = self._recurrence_html()
        
        # Pre-split interpretation to avoid backslash in f-string expression
        interp_paragraphs = interpretation.split('\n\n')
        interp_first = interp_paragraphs[0] if interp_paragraphs else ''
        interp_rest = interp_paragraphs[1:] if len(interp_paragraphs) > 1 else []

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>SpliceGAIP Analysis Report</title>
<style>
 body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; color: #1a1a1a; max-width: 960px; margin: 2rem auto; padding: 0 1.2rem; line-height: 1.55; }}
 h1 {{ border-bottom: 3px solid #0072B2; padding-bottom: .4rem; }}
 h2 {{ color: #005485; margin-top: 2.2rem; }}
 table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .92rem; }}
 th, td {{ border: 1px solid #d8d8d8; padding: .4rem .6rem; text-align: left; }}
 th {{ background: #eef5fa; }}
 figure {{ margin: 1.6rem 0; text-align: center; }}
 figure img {{ max-width: 100%; border: 1px solid #e2e2e2; }}
 figcaption {{ font-size: .88rem; color: #444; text-align: left; margin-top: .4rem; }}
 .meta {{ color: #555; font-size: .9rem; }}
 .callout {{ background: #fdf6ec; border-left: 4px solid #D55E00; padding: .8rem 1rem; }}
 code {{ background: #f4f4f4; padding: .1rem .3rem; }}
 .ai-lead {{ font-size: 1.05rem; font-weight: 600; color: #005485; }}
 .ai-highlights li {{ margin-bottom: .3rem; }}
 table.ai-table th {{ background: #eef7ee; }}
 .ai-note {{ background: #f4f8fc; border-left: 4px solid #1c69d4; padding: .6rem .8rem; font-size: .9rem; }}
</style>
</head>
<body>
<h1>SpliceGAIP Analysis Report</h1>
<p class="meta">Project <b>{html.escape(context.project_id)}</b> &middot; generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} &middot; {REPORT_VERSION}</p>
<p class="meta">User query: &ldquo;{html.escape(context.query)}&rdquo; &middot; input: {html.escape(str(dataset.source_dir))} ({html.escape(dataset.source_format)})</p>

<h2>1. Summary</h2>
<p>{html.escape(interp_first)}</p>
<ul>
{''.join(f'<li>{html.escape(line)}</li>' for line in interp_rest)}
</ul>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{''.join(f'<tr><td>{html.escape(key)}</td><td>{html.escape(str(value))}</td></tr>' for key, value in summary_stats.items())}
</table>

<h2>2. Methods</h2>
<p>Alternative splicing events were parsed from <code>{html.escape(dataset.source_format)}</code> output and
normalized to the SpliceGAIP <code>AS_event_master</code> contract (event_id, gene_id, gene_symbol, event_type,
coordinates, per-sample PSI, delta_PSI, p_value, FDR). Significance filtering applied
FDR &lt; {_fmt(context.settings.analysis.fdr_threshold)} and |delta PSI| &gt; {_fmt(context.settings.analysis.delta_psi_threshold)}
with quality gating (minimum {context.settings.analysis.min_support_reads} supporting reads,
minimum {context.settings.analysis.min_valid_samples} valid samples, single-sample-driven and
mapping-ambiguity events excluded). Candidates were ranked by a composite score
(0.4 significance, 0.3 effect size, 0.2 biological relevance, 0.1 literature evidence).
Functional enrichment used a hypergeometric over-representation test against the supplied
background annotation. Figures were rendered with matplotlib; the report was generated by
SpliceGAIP's report agent.</p>

<h2>3. Results</h2>
<h3>3.1 Top candidate events</h3>
<table>
<tr><th>Rank</th><th>Gene</th><th>Event type</th><th>delta PSI</th><th>FDR</th><th>Score</th></tr>
{candidate_rows or '<tr><td colspan="6">No significant events passed the configured gates.</td></tr>'}
</table>
<h3>3.2 Functional enrichment</h3>
<table>
<tr><th>Term</th><th>Ontology</th><th>Genes</th><th>Fold enrichment</th><th>FDR</th></tr>
{enrichment_rows or '<tr><td colspan="5">No enriched terms (no annotation supplied or nothing significant).</td></tr>'}
</table>
{hypothesis_tests}

<h2>4. Figures</h2>
{figure_blocks or '<p>No figures were generated.</p>'}

<h2>5. Biological interpretation</h2>
<p>{html.escape(interpretation).replace(chr(10) + chr(10), '</p><p>')}</p>
<h3>5.1 Literature evidence</h3>
<ul>{evidence_items or '<li>No literature records available for the candidate genes.</li>'}</ul>
{('<h3>5.2 AI-assisted interpretation</h3>' + ai_narrative) if ai_narrative else ''}
{('<h3>5.3 AI gene annotations</h3>' + ai_gene_notes) if ai_gene_notes else ''}
{('<h3>5.4 AI evidence summaries</h3>' + ai_evidence_summary) if ai_evidence_summary else ''}
{external_findings}
{recurrence_section}

<h2>6. Limitations</h2>
<ul>{limitation_items}</ul>

<h2>7. References</h2>
<ul>{reference_items or '<li>No external references were used.</li>'}</ul>

{('<h2>8. AI-generated hypotheses and validation plan</h2>' + ai_hypotheses) if ai_hypotheses else ''}
{('<h3>8.1 Automated critique of the interpretation</h3>' + ai_critique) if ai_critique else ''}
<h2>{provenance_number}. AI provenance</h2>
{ai_model}
<p class="meta">Evidence sources: {html.escape('; '.join(context.knowledge.describe_sources()))}.
Workflow log entries: {len(context.workflow_log)}. All results are reproducible from the archived input data and parameters.</p>
</body>
</html>
"""

    # -- PDF --------------------------------------------------------------
    def render_pdf(self, path: Path) -> bool:
        """Render the PDF report with reportlab; returns False when unavailable."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                Image,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except Exception:
            return False

        context = self.context
        interpretation = build_interpretation(context)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("SpliceTitle", parent=styles["Title"], fontSize=18, spaceAfter=6)
        heading_style = ParagraphStyle("SpliceHeading", parent=styles["Heading2"], textColor=colors.HexColor("#005485"))
        body_style = styles["BodyText"]

        story: list[Any] = [
            Paragraph("SpliceGAIP Analysis Report", title_style),
            Paragraph(
                f"Project {context.project_id} &middot; {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                styles["Normal"],
            ),
            Paragraph(f"User query: {context.query}", styles["Normal"]),
            Spacer(1, 6 * mm),
            Paragraph("1. Summary", heading_style),
            Paragraph(interpretation.replace("\n\n", "</p><p>"), body_style),
            Spacer(1, 4 * mm),
            Paragraph("2. Methods", heading_style),
            Paragraph(
                "Events were normalized to the AS_event_master contract; significance gates "
                f"FDR &lt; {context.settings.analysis.fdr_threshold} and |delta PSI| &gt; "
                f"{context.settings.analysis.delta_psi_threshold} with quality gating; candidates ranked by "
                "composite score (0.4 significance / 0.3 effect / 0.2 biology / 0.1 literature); "
                "enrichment by hypergeometric test against the supplied background.",
                body_style,
            ),
            Spacer(1, 4 * mm),
            Paragraph("3. Results", heading_style),
        ]

        if context.candidates:
            table_data = [["Rank", "Gene", "Type", "delta PSI", "FDR", "Score"]]
            table_data.extend(
                [
                    str(index),
                    item.gene_symbol or item.gene_id,
                    item.event_type,
                    _fmt(item.delta_psi),
                    _fmt(item.fdr),
                    f"{item.score:.3f}",
                ]
                for index, item in enumerate(context.candidates[:15], start=1)
            )
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF5FA")),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D8D8")),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(table)

        if context.enrichment:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("3.2 Functional enrichment", heading_style))
            enrichment_data = [["Term", "Ontology", "Genes", "Fold", "FDR"]]
            enrichment_data.extend(
                [item.term, item.ontology, str(item.gene_count), str(item.fold_enrichment), _fmt(item.fdr)]
                for item in context.enrichment[:12]
            )
            enrichment_table = Table(enrichment_data, repeatRows=1)
            enrichment_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF5FA")),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D8D8")),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(enrichment_table)

        tests = list(getattr(context, "hypotheses", None) or [])
        if tests:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("3.3 Statistical hypothesis tests", heading_style))
            story.append(
                Paragraph(
                    "Pre-registered tests computed locally (scipy) before interpretation; "
                    "p-values are Benjamini-Hochberg adjusted across the test family.",
                    styles["Italic"],
                )
            )
            test_data = [["Hypothesis (H0)", "Test", "Statistic", "p", "BH q", "n", "Verdict"]]
            test_data.extend(
                [
                    item.title,
                    item.method,
                    _fmt(item.statistic),
                    _fmt(item.p_value),
                    _fmt(item.fdr),
                    str(item.n),
                    item.verdict,
                ]
                for item in tests
            )
            test_table = Table(test_data, repeatRows=1)
            test_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF5FA")),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D8D8")),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.append(test_table)
            for item in tests:
                story.append(Paragraph(f"&bull; <b>{item.code}</b>: {item.interpretation}", body_style))

        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("4. Figures", heading_style))
        for figure in context.figures:
            if figure.png_path.is_file():
                story.append(Spacer(1, 3 * mm))
                story.append(Paragraph(figure.title, styles["Heading4"]))
                story.append(Image(str(figure.png_path), width=150 * mm, height=100 * mm, kind="proportional"))
                story.append(Paragraph(figure.caption, styles["Italic"]))

        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("5. Biological interpretation", heading_style))
        story.append(Paragraph(interpretation.replace("\n\n", "</p><p>"), body_style))

        narrative = self._narrative()
        if narrative.get("source") == "llm":
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("5.2 AI-assisted interpretation", heading_style))
            lead = str(narrative.get("lead") or "").strip()
            if lead:
                story.append(Paragraph(lead, body_style))
            for paragraph in narrative.get("paragraphs") or []:
                story.append(Paragraph(str(paragraph), body_style))
            for highlight in narrative.get("highlights") or []:
                story.append(Paragraph(f"&bull; {highlight}", body_style))
        gene_notes = self._insights().get("gene_notes")
        if isinstance(gene_notes, dict) and gene_notes:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("5.3 AI gene annotations", heading_style))
            for gene, text in gene_notes.items():
                story.append(Paragraph(f"<b>{gene}</b> &mdash; {text}", body_style))
        insights = self._insights()
        block = insights.get("hypotheses")
        if isinstance(block, dict) and block.get("source") == "llm":
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("8. AI-generated hypotheses and validation plan", heading_style))
            for title, key in (
                ("Hypotheses", "hypotheses"),
                ("Validation plan", "validations"),
                ("Follow-up analyses", "followups"),
            ):
                items = [str(item) for item in block.get(key) or [] if str(item).strip()]
                if items:
                    story.append(Paragraph(title, styles["Heading4"]))
                    for item in items:
                        story.append(Paragraph(f"&bull; {item}", body_style))
        critique_block = insights.get("critique")
        if isinstance(critique_block, dict) and critique_block.get("source") == "llm":
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("8.1 Automated critique", heading_style))
            if critique_block.get("verdict"):
                story.append(Paragraph(str(critique_block["verdict"]), body_style))
            for issue in critique_block.get("issues") or []:
                story.append(Paragraph(f"&bull; {issue}", body_style))

        external = getattr(context, "external", None) or {}
        if external:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("5.5 External knowledge findings", heading_style))
            annotations = external.get("gene_annotation") or {}
            for gene, value in list(annotations.items())[:12]:
                value = value or {}
                name = str(value.get("name") or "")
                identifier = str(value.get("ensembl_gene") or value.get("entrez") or "")
                text = f"<b>{gene}</b>"
                if name:
                    text += f" &mdash; {name}"
                if identifier:
                    text += f" ({identifier})"
                story.append(Paragraph(text, body_style))
            pathways = external.get("pathways") or {}
            if pathways.get("rows"):
                story.append(
                    Paragraph(
                        f"Pathway source: {pathways.get('source', 'external')}",
                        styles["Italic"],
                    )
                )
                for row in pathways["rows"][:8]:
                    story.append(
                        Paragraph(
                            f"&bull; {row.get('term')} ({row.get('library') or row.get('ontology')}) "
                            f"fold={_fmt(row.get('fold_enrichment'))} FDR={_fmt(row.get('fdr'))}",
                            body_style,
                        )
                    )
            for gene, payload in list((external.get("interpretation") or {}).items())[:8]:
                summary = str((payload or {}).get("summary") or "").strip()
                if summary:
                    story.append(
                        Paragraph(f"&bull; <b>{gene}</b>: {summary[:300]}", body_style)
                    )

        # -- 5.6 Lab-level recurrence (Step 3) ---------------------------------
        recurrent = self.context.external.get("recurrent_genes") or []
        if recurrent:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("5.6 Lab-level recurrence", heading_style))
            story.append(
                Paragraph(
                    "The following genes appeared in multiple prior projects and also rank highly in this analysis:",
                    body_style,
                )
            )
            table_data = [
                ["Gene", "Projects", "Total Hits", "Avg |ΔPSI|", "Event Types"]
            ]
            for item in recurrent[:10]:
                avg_dpsi = item.get("avg_delta_psi")
                avg_dpsi_str = f"{abs(avg_dpsi):.3f}" if avg_dpsi is not None else "N/A"
                event_types = ", ".join(item.get("event_types", [])[:3])
                table_data.append(
                    [
                        item["gene"],
                        str(item["project_count"]),
                        str(item["total_hits"]),
                        avg_dpsi_str,
                        event_types,
                    ]
                )
            recurrence_table = Table(table_data, colWidths=[80, 50, 60, 70, 120], repeatRows=1)
            recurrence_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF5FA")),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D8D8")),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(recurrence_table)

        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("6. Limitations", heading_style))
        for limitation in self._limitations():
            story.append(Paragraph(f"&bull; {limitation}", body_style))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("7. References", heading_style))
        for reference in self._references():
            story.append(Paragraph(f"&bull; {reference}", body_style))

        has_llm_hypotheses = isinstance(block, dict) and block.get("source") == "llm"
        provenance_number_pdf = "9" if has_llm_hypotheses else "8"
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"{provenance_number_pdf}. AI provenance", heading_style))
        if not insights.get("enabled"):
            story.append(
                Paragraph(
                    "AI enrichment: not active (no model endpoint configured). "
                    "All text in this report is deterministic.",
                    body_style,
                )
            )
        else:
            status = insights.get("status") if isinstance(insights.get("status"), dict) else {}
            story.append(
                Paragraph(
                    f"AI enrichment: {insights.get('model') or status.get('model') or 'configured model'} "
                    f"&middot; {status.get('base_url') or ''} "
                    f"&middot; {int(insights.get('calls') or status.get('call_count') or 0)} model calls.",
                    body_style,
                )
            )
        story.append(
            Paragraph(
                "All results are reproducible from the archived input data and parameters.",
                body_style,
            )
        )

        doc = SimpleDocTemplate(str(path), pagesize=A4, title="SpliceGAIP Analysis Report")
        doc.build(story)
        return True

    # -- AI insight helpers -----------------------------------------------
    def _insights(self) -> dict[str, Any]:
        """Model-enriched insights for this run (empty in deterministic mode)."""
        raw = getattr(self.context, "llm_insights", None) or {}
        return raw if isinstance(raw, dict) else {}

    def _narrative(self) -> dict[str, Any]:
        narrative = self._insights().get("narrative")
        return narrative if isinstance(narrative, dict) else {}

    def _ai_narrative_html(self) -> str:
        narrative = self._narrative()
        if not narrative or narrative.get("source") != "llm":
            return ""
        lead = str(narrative.get("lead") or "").strip()
        paragraphs = [str(item) for item in narrative.get("paragraphs") or [] if str(item).strip()]
        highlights = [str(item) for item in narrative.get("highlights") or [] if str(item).strip()]
        if not (lead or paragraphs or highlights):
            return ""
        parts: list[str] = []
        if lead:
            parts.append(f'<p class="ai-lead">{html.escape(lead)}</p>')
        parts.extend(f"<p>{html.escape(item)}</p>" for item in paragraphs)
        if highlights:
            parts.append(
                '<ul class="ai-highlights">'
                + "".join(f"<li>{html.escape(item)}</li>" for item in highlights)
                + "</ul>"
            )
        return "".join(parts)

    def _ai_gene_notes_html(self) -> str:
        notes = self._insights().get("gene_notes")
        if not isinstance(notes, dict) or not notes:
            return ""
        rows = "".join(
            f"<tr><td><b>{html.escape(str(gene))}</b></td><td>{html.escape(str(text))}</td></tr>"
            for gene, text in notes.items()
            if str(text).strip()
        )
        return (
            '<table class="ai-table"><tr><th>Gene</th><th>AI annotation (hypothesis-generating)</th></tr>'
            f"{rows}</table>"
        )

    def _ai_evidence_summary_html(self) -> str:
        summaries = self._insights().get("evidence_summaries")
        if not isinstance(summaries, dict) or not summaries:
            return ""
        rows = "".join(
            f"<tr><td><b>{html.escape(str(gene))}</b></td><td>{html.escape(str(text))}</td></tr>"
            for gene, text in summaries.items()
            if str(text).strip()
        )
        return (
            '<table class="ai-table"><tr><th>Gene</th><th>Evidence summary (from retrieved records)</th></tr>'
            f"{rows}</table>"
        )

    def _ai_hypotheses_html(self) -> str:
        insights = self._insights()
        block = insights.get("hypotheses")
        if not isinstance(block, dict) or block.get("source") != "llm":
            return ""
        pieces: list[str] = []
        for title, key in (
            ("Hypotheses", "hypotheses"),
            ("Validation plan", "validations"),
            ("Follow-up analyses", "followups"),
        ):
            items = [str(item) for item in block.get(key) or [] if str(item).strip()]
            if items:
                pieces.append(
                    f"<h3>{html.escape(title)}</h3><ul class=\"ai-highlights\">"
                    + "".join(f"<li>{html.escape(item)}</li>" for item in items)
                    + "</ul>"
                )
        return "".join(pieces)

    def _ai_critique_html(self) -> str:
        block = self._insights().get("critique")
        if not isinstance(block, dict) or block.get("source") != "llm":
            return ""
        verdict = str(block.get("verdict") or "").strip()
        issues = [str(item) for item in block.get("issues") or [] if str(item).strip()]
        parts = [f"<p>{html.escape(verdict)}</p>"] if verdict else []
        if issues:
            parts.append("<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in issues) + "</ul>")
        elif not verdict:
            return ""
        return "".join(parts)

    def _ai_model_html(self) -> str:
        insights = self._insights()
        if not insights.get("enabled"):
            return (
                '<p class="meta">AI enrichment: not active '
                "(no model endpoint configured). All text above is deterministic.</p>"
            )
        status = insights.get("status") if isinstance(insights.get("status"), dict) else {}
        return (
            '<p class="meta">AI enrichment: '
            f"<b>{html.escape(str(insights.get('model') or status.get('model') or ''))}</b> "
            f"&middot; {html.escape(str(status.get('base_url') or ''))} "
            f"&middot; {int(insights.get('calls') or status.get('call_count') or 0)} model calls "
            f"&middot; features: {html.escape(', '.join(str(f) for f in (insights.get('features') or [])))}"
            "</p>"
        )

    # -- Phase 2 helpers ---------------------------------------------------
    def _hypothesis_html(self) -> str:
        """Pre-registered statistical tests the agent ran on its own result."""
        tests = list(getattr(self.context, "hypotheses", None) or [])
        if not tests:
            return ""
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(item.title)}</td>"
            f"<td>{html.escape(item.method)}</td>"
            f"<td>{_fmt(item.statistic)}</td>"
            f"<td>{_fmt(item.p_value)}</td>"
            f"<td>{_fmt(item.fdr)}</td>"
            f"<td>{item.n}</td>"
            f"<td>{html.escape(item.verdict)}</td>"
            "</tr>"
            for item in tests
        )
        notes = "".join(
            f"<li><b>{html.escape(item.code)}</b>: {html.escape(item.interpretation)}</li>"
            for item in tests
        )
        return (
            '<h3>3.3 Statistical hypothesis tests</h3>'
            '<p class="meta">Pre-registered tests computed locally (scipy) before interpretation; '
            'p-values are Benjamini-Hochberg adjusted across the test family.</p>'
            "<table>"
            "<tr><th>Hypothesis (H0)</th><th>Test</th><th>Statistic</th><th>p</th>"
            "<th>BH q</th><th>n</th><th>Verdict</th></tr>"
            f"{rows}"
            "</table>"
            '<p class="meta">Reading of each test:</p>'
            f"<ul>{notes}</ul>"
        )

    def _external_html(self) -> str:
        """Findings retrieved from external knowledge sources (skills)."""
        external = getattr(self.context, "external", None) or {}
        if not external:
            return ""
        blocks: list[str] = []
        annotations = external.get("gene_annotation") or {}
        if annotations:
            rows = "".join(
                "<tr>"
                f"<td>{html.escape(str(gene))}</td>"
                f"<td>{html.escape(str((value or {}).get('name') or ''))}</td>"
                f"<td>{html.escape(str((value or {}).get('gene_type') or ''))}</td>"
                f"<td>{html.escape(str((value or {}).get('ensembl_gene') or (value or {}).get('entrez') or ''))}</td>"
                "</tr>"
                for gene, value in list(annotations.items())[:15]
            )
            blocks.append(
                "<table>"
                "<tr><th>Gene</th><th>Name</th><th>Type</th><th>Ensembl / Entrez</th></tr>"
                f"{rows}"
                "</table>"
            )
        pathways = external.get("pathways") or {}
        if pathways.get("rows"):
            source = str(pathways.get("source") or "external")
            rows = "".join(
                "<tr>"
                f"<td>{html.escape(str(row.get('term') or ''))}</td>"
                f"<td>{html.escape(str(row.get('library') or row.get('ontology') or ''))}</td>"
                f"<td>{_fmt(row.get('fold_enrichment'))}</td>"
                f"<td>{_fmt(row.get('fdr'))}</td>"
                "</tr>"
                for row in pathways["rows"][:12]
            )
            blocks.append(
                f'<p class="meta">Pathway source: {html.escape(source)}</p>'
                "<table>"
                "<tr><th>Term</th><th>Library</th><th>Fold</th><th>FDR</th></tr>"
                f"{rows}"
                "</table>"
            )
        literature = external.get("literature") or {}
        if literature:
            items = "".join(
                f"<li><b>{html.escape(str(gene))}</b>: "
                f"{len((entry or {}).get('records') or [])} record(s) for "
                f"&ldquo;{html.escape(str((entry or {}).get('query') or ''))}&rdquo;</li>"
                for gene, entry in list(literature.items())[:10]
            )
            blocks.append(f"<ul>{items}</ul>")
        interpretation = external.get("interpretation") or {}
        if interpretation:
            items = []
            for gene, payload in list(interpretation.items())[:10]:
                payload = payload or {}
                summary = str(payload.get("summary") or "").strip()
                if summary:
                    items.append(
                        f"<li><b>{html.escape(str(gene))}</b> ({html.escape(str(payload.get('event_type') or ''))}): "
                        f"{html.escape(summary[:400])}</li>"
                    )
            if items:
                blocks.append("<ul>" + "".join(items) + "</ul>")
        if not blocks:
            return ""
        return "<h3>5.5 External knowledge findings</h3>" + "".join(blocks)

    def _recurrence_html(self) -> str:
        """Render section 5.6: Lab-level recurrence."""
        external = getattr(self.context, "external", None) or {}
        recurrent = external.get("recurrent_genes") or []
        if not recurrent:
            return ""

        rows = []
        for item in recurrent[:10]:
            avg_dpsi = item.get("avg_delta_psi")
            avg_dpsi_str = f"{abs(avg_dpsi):.3f}" if avg_dpsi is not None else "N/A"
            event_types = ", ".join(item.get("event_types", [])[:3])
            rows.append(
                f"<tr><td>{item['gene']}</td><td>{item['project_count']}</td>"
                f"<td>{item['total_hits']}</td><td>{avg_dpsi_str}</td>"
                f"<td>{event_types}</td></tr>"
            )

        html = (
            "<h3>5.6 Lab-level recurrence</h3>"
            "<p class='meta'>Genes that appeared in multiple prior projects and also rank highly in this analysis:</p>"
            "<table>"
            "<tr><th>Gene</th><th>Projects</th><th>Total Hits</th><th>Avg |ΔPSI|</th><th>Event Types</th></tr>"
            + "".join(rows)
            + "</table>"
        )
        return html

    # -- helpers ----------------------------------------------------------
    def _embed(self, path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("ascii")

    def _summary_stats(self) -> dict[str, Any]:
        context = self.context
        stats = {
            "input format": context.dataset.source_format,
            "total AS events": len(context.dataset.events),
            "significant events": len(context.significant_events),
            "candidates ranked": len(context.candidates),
            "enriched terms": len(context.enrichment),
            "figures": len(context.figures),
            "samples": len(context.dataset.samples),
        }
        if context.filter_report is not None:
            stats["filter"] = context.filter_report.as_dict()
        if getattr(context, "hypotheses", None):
            stats["hypothesis tests"] = (
                f"{len(context.hypotheses)} run, "
                f"{sum(1 for item in context.hypotheses if item.verdict == 'rejected')} rejected"
            )
        return stats

    def _limitations(self) -> list[str]:
        context = self.context
        # When the model enrichment ran, it returns the deterministic list
        # plus the additional limitations it derived from the same facts.
        extended = self._insights().get("limitations")
        if isinstance(extended, list) and extended:
            return [str(item) for item in extended]
        limitations: list[str] = []
        if not context.dataset.annotation:
            limitations.append(
                "No gene annotation table was supplied; functional enrichment was not performed."
            )
        if not any(entries for entries in context.evidence.values()):
            limitations.append(
                "No literature records were available for the candidate genes; interpretation "
                "is limited to statistical evidence."
            )
        if context.validation is not None and context.validation.warnings:
            limitations.extend(issue.message for issue in context.validation.warnings)
        limitations.append(
            "Candidate prioritization is hypothesis-generating: associations require experimental "
            "validation before biological conclusions are drawn."
        )
        limitations.append(
            "Statistical gates (FDR and |delta PSI|) are platform defaults; sensitivity analyses "
            "with alternative thresholds are recommended."
        )
        return limitations

    def _references(self) -> list[str]:
        context = self.context
        references: list[str] = []
        for entries in context.evidence.values():
            for entry in entries:
                if entry.pmid:
                    references.append(f"PMID {entry.pmid} ({entry.source})")
        if not references:
            references.append(
                "SpliceGAIP curated knowledge base (bundled, offline). No external references used."
            )
        return list(dict.fromkeys(references))[:20]

    # -- entry point ------------------------------------------------------
    def generate(self, output_dir: str, formats: Sequence[str] = ("html", "pdf")) -> dict[str, Path]:
        """Write the report into ``output_dir`` and return the produced paths."""
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        if "html" in formats:
            html_path = directory / "report.html"
            html_path.write_text(self.render_html(), encoding="utf-8")
            paths["html"] = html_path
        if "pdf" in formats:
            pdf_path = directory / "report.pdf"
            if self.render_pdf(pdf_path):
                paths["pdf"] = pdf_path
        return paths
