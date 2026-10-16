"""Action registry: everything the agent is able to do.

Every action is a plain function ``(context, state, **args) -> str``. The
registry is what the decision engine may choose from; it wraps the eight
existing platform tools and adds the four capabilities that make
self-decision possible (profile, quality assessment, adaptive thresholds,
per-gene deep dive).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from splicegaip.splicing.filtering import FilterSettings, passes_quality, passes_significance
from splicegaip.tools.context import RunContext

from .hypothesis import run_hypothesis_tests, text_summary
from .profile import build_profile, profile_text
from .skills_bridge import SkillBridge, SkillCall
from .state import AgentState
from .threshold_bandit import ThresholdBandit, compute_reward

#: Threshold grids the adaptive policy may choose from (strict -> loose).
FDR_GRID: tuple[float, ...] = (0.01, 0.05, 0.1, 0.2)
DPSI_GRID: tuple[float, ...] = (0.2, 0.15, 0.1, 0.05)


@dataclass(frozen=True)
class Action:
    """One callable capability of the agent."""

    name: str
    description: str
    func: Callable[..., str]
    #: Facts that must be true before the action makes sense.
    requires: tuple[str, ...] = ()


# --------------------------------------------------------------------------
# New: sensing / self-tuning actions
# --------------------------------------------------------------------------


def profile_dataset(context: RunContext, state: AgentState) -> str:
    """Profile the dataset before deciding anything (the 'sense' phase)."""
    state.profile = build_profile(context)
    context.log("agent", "profile_dataset", "ok", profile_text(state.profile)[:400])
    return profile_text(state.profile)


def assess_quality(context: RunContext, state: AgentState) -> str:
    """Assess how the quality gates behave at the current thresholds."""
    analysis = context.settings.analysis
    settings = FilterSettings(
        fdr_threshold=state.params.get("fdr", analysis.fdr_threshold),
        delta_psi_threshold=state.params.get("delta_psi", analysis.delta_psi_threshold),
        min_support_reads=analysis.min_support_reads,
        min_valid_samples=analysis.min_valid_samples,
    )
    excluded: dict[str, int] = {}
    passed = 0
    for event in context.dataset.events:
        if not passes_significance(event, settings):
            excluded["not_significant"] = excluded.get("not_significant", 0) + 1
            continue
        ok, reason = passes_quality(event, settings)
        if not ok:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        passed += 1
    state.facts["quality"] = {
        "passing": passed,
        "excluded": excluded,
        "thresholds": {
            "fdr": settings.fdr_threshold,
            "delta_psi": settings.delta_psi_threshold,
        },
    }
    breakdown = ", ".join(f"{key}={value}" for key, value in sorted(excluded.items())) or "none"
    message = (
        f"Quality assessment at FDR<{settings.fdr_threshold}, "
        f"|dPSI|>{settings.delta_psi_threshold}: {passed} events pass; excluded: {breakdown}."
    )
    context.log("agent", "assess_quality", "ok", message)
    return message


def _count_at(context: RunContext, fdr: float, dpsi: float) -> int:
    analysis = context.settings.analysis
    settings = FilterSettings(
        fdr_threshold=fdr,
        delta_psi_threshold=dpsi,
        min_support_reads=analysis.min_support_reads,
        min_valid_samples=analysis.min_valid_samples,
    )
    total = 0
    for event in context.dataset.events:
        if not passes_significance(event, settings):
            continue
        ok, _reason = passes_quality(event, settings)
        if ok:
            total += 1
    return total


def adapt_thresholds(
    context: RunContext,
    state: AgentState,
    target: int | None = None,
    strategy: str = "balanced",
) -> str:
    """Choose FDR / |dPSI| thresholds from the data itself.

    Uses multi-armed bandit learning to improve threshold selection over time.
    
    ``balanced`` aims for a workable candidate set around ``target``
    (default: :attr:`~splicegaip.config.AgentSettings.target_significant`);
    ``strict`` always prefers the tightest gate that still yields events;
    ``exploratory`` loosens to the grid edge to rescue a dataset where
    nothing is significant at the configured thresholds.
    """
    analysis = context.settings.analysis
    goal_target = target or int(
        getattr(context.settings, "agent", None).target_significant
        if getattr(context.settings, "agent", None)
        else 100
    )
    
    # Load bandit state from previous runs
    bandit = ThresholdBandit()
    try:
        from pathlib import Path
        bandit_dir = Path(context.project_id).parent / ".splicegaip" / "bandit"
        bandit_dir.mkdir(parents=True, exist_ok=True)
        bandit_file = bandit_dir / "threshold_bandit.json"
        bandit.load(bandit_file)
    except Exception:
        pass  # Start fresh if no history
    
    counts: dict[tuple[float, float], int] = {}
    for fdr in FDR_GRID:
        for dpsi in DPSI_GRID:
            counts[(fdr, dpsi)] = _count_at(context, fdr, dpsi)

    floor = max(5, int(goal_target * 0.2))
    ceiling = max(int(goal_target * 3), floor + 1)

    if strategy == "strict":
        usable = [key for key, value in counts.items() if value >= floor]
        choice = min(usable, key=lambda key: (key[0], -key[1])) if usable else max(
            counts, key=lambda key: counts[key]
        )
    elif strategy == "exploratory":
        usable = [key for key, value in counts.items() if value > 0]
        choice = (
            min(usable, key=lambda key: (key[0], -key[1]))
            if usable
            else max(counts, key=lambda key: counts[key])
        )
    else:  # balanced - use bandit learning
        # Cross-run experience wins when it still works on this dataset.
        hint = state.facts.get("episodic_hint")
        if isinstance(hint, dict) and hint.get("fdr") is not None:
            hinted = (float(hint["fdr"]), float(hint.get("delta_psi", DPSI_GRID[-1])))
            if hinted in counts and counts[hinted] >= floor:
                fdr, dpsi = hinted
                count = counts[hinted]
                return _apply_params(
                    context, state, fdr, dpsi, count, goal_target, source="episodic memory"
                )
        
        # Use bandit to choose from viable candidates
        usable = [key for key, value in counts.items() if floor <= value <= ceiling]
        if not usable:
            usable_any = [key for key, value in counts.items() if value >= floor]
            usable = usable_any if usable_any else list(counts.keys())
        
        choice = bandit.choose(usable, counts, goal_target)
        
        # Record reward for this choice
        count = counts[choice]
        reward = compute_reward(count, goal_target, choice[0], choice[1])
        bandit.update(choice[0], choice[1], reward)
        
        # Save updated bandit state
        try:
            bandit.save(bandit_file)
        except Exception:
            pass
        
        return _apply_params(
            context, state, choice[0], choice[1], count, goal_target,
            source=f"bandit+grid search ({strategy}, ε={bandit.epsilon:.2f})"
        )

    return _apply_params(
        context, state, choice[0], choice[1], counts[choice], goal_target,
        source=f"grid search ({strategy})",
    )


def _apply_params(
    context: RunContext,
    state: AgentState,
    fdr: float,
    dpsi: float,
    count: int,
    goal_target: int,
    *,
    source: str,
) -> str:
    """Persist the chosen thresholds on the state and log the decision."""
    previous = dict(state.params)
    top_n = max(5, min(context.settings.analysis.top_candidates, max(count, 5)))
    state.params.update(
        {
            "fdr": fdr,
            "delta_psi": dpsi,
            "top_n": top_n,
            "expected_significant": count,
            "source": source,
        }
    )
    message = (
        f"Adapted thresholds to FDR<{fdr}, |dPSI|>{dpsi} ({source}): "
        f"expected {count} significant events (target {goal_target}); top_n set to {top_n}."
    )
    if previous:
        message += f" Previous: {previous}."
    context.log("agent", "adapt_thresholds", "ok", message)
    history = list(state.facts.get("params_history", []))
    history.append(dict(state.params))
    state.facts["params_history"] = history
    return message


def deep_dive_gene(context: RunContext, state: AgentState, gene: str) -> str:
    """Zoom into one gene: its events, effect sizes and literature evidence."""
    gene = str(gene).strip()
    if not gene:
        return "deep_dive_gene requires a gene symbol or id."
    matched = [
        event
        for event in context.dataset.events
        if gene.lower() in {(event.gene_symbol or "").lower(), (event.gene_id or "").lower()}
    ]
    if not matched:
        message = f"No events found for gene {gene} in this dataset."
        context.log("agent", "deep_dive_gene", "skipped", message)
        return message
    deltas = [abs(event.delta_psi) for event in matched if event.delta_psi is not None]
    fdrs = [event.fdr for event in matched if event.fdr is not None]
    types: dict[str, int] = {}
    for event in matched:
        types[event.event_type] = types.get(event.event_type, 0) + 1
    significant_ids = {event.event_id for event in context.significant_events}
    significant = sum(1 for event in matched if event.event_id in significant_ids)
    evidence = context.knowledge.collect_evidence([gene], max_per_gene=3)
    if evidence.get(gene):
        context.evidence.setdefault(gene, []).extend(evidence[gene])
    summary_bits = ", ".join(f"{key}={value}" for key, value in sorted(types.items()))
    message = (
        f"Deep dive {gene}: {len(matched)} event(s) ({summary_bits}); "
        f"{significant} significant; "
        f"mean |dPSI|={round(sum(deltas) / len(deltas), 3) if deltas else 'NA'}; "
        f"min FDR={min(fdrs) if fdrs else 'NA'}; "
        f"literature records={len(evidence.get(gene, []))}."
    )
    state.facts.setdefault("deep_dives", []).append(gene)
    context.log("agent", "deep_dive_gene", "ok", message)
    return message


# --------------------------------------------------------------------------
# New (Phase 2): hypothesis testing and external knowledge skills
# --------------------------------------------------------------------------


def _bridge(state: AgentState, context: RunContext) -> SkillBridge:
    """Lazily create the (budgeted) bridge to the async external skills."""
    if state.bridge is None:
        state.bridge = SkillBridge.from_settings(context.settings)
    return state.bridge


def test_hypothesis(context: RunContext, state: AgentState, alpha: float | None = None) -> str:
    """Challenge the current result with pre-registered statistical tests.

    Nothing here is optional prose: every test either supports the result or
    exposes a confound, and the outcome is written into the report.
    """
    results = run_hypothesis_tests(context, alpha=alpha or 0.05)
    context.hypotheses = results
    state.facts["hypotheses"] = [item.as_dict() for item in results]
    state.facts["hypothesis_confounds"] = [
        item.code for item in results if item.code in {"coverage_confound", "event_type_bias"} and item.verdict == "rejected"
    ]
    state.facts["hypotheses_run"] = bool(results)
    summary = text_summary(results)
    context.log("agent", "test_hypothesis", "ok", summary.replace("\n", " | ")[:400])
    return summary


def annotate_genes(context: RunContext, state: AgentState, genes: list[str] | None = None) -> str:
    """Annotate candidate genes from an external source (MyGene/Ensembl)."""
    target = [str(gene) for gene in (genes or context.top_genes(12))]
    if not target:
        return "annotate_genes skipped: no candidate genes available."
    bridge = _bridge(state, context)
    known: dict[str, Any] = dict(state.facts.get("gene_annotations") or {})
    todo = [gene for gene in target if gene not in known]
    if not todo:
        return f"All {len(target)} candidate genes are already annotated."
    if bridge.spent():
        return f"annotate_genes skipped: external call budget exhausted ({bridge.used}/{bridge.budget})."

    try:
        from splicegaip.integrations import mygene_client

        if mygene_client.backend_available():
            annotated = mygene_client.annotate(todo, timeout=bridge.timeout)
            bridge.calls.append(
                SkillCall(
                    "gene_annotation",
                    {"genes": todo[:8]},
                    "ok" if annotated else "failed",
                    "MyGene.info batch query",
                )
            )
            if annotated:
                known.update({key: value for key, value in annotated.items() if not value.get("not_found")})
    except Exception:  # noqa: BLE001 - optional backend
        annotated = None

    source = "MyGene.info" if any("MyGene" in str(v.get("source", "")) for v in known.values()) else ""
    if not source:
        from splicegaip.skills.gene_annotation import GeneAnnotationSkill

        for gene in todo[:3]:
            result = bridge.run_skill(
                "gene_annotation",
                GeneAnnotationSkill,
                gene_symbol=gene,
                include_splicing=True,
                include_clinical=True,
            )
            if result is not None:
                data = dict(result.data or {})
                data["source"] = "GeneAnnotationSkill"
                known[gene] = data
        source = "built-in GeneAnnotationSkill"

    if not known:
        message = (
            f"External gene annotation unavailable for {len(todo)} gene(s); "
            "the analysis continues without annotation."
        )
        context.log("agent", "annotate_genes", "skipped", message)
        return message

    state.facts["gene_annotations"] = known
    state.facts["annotated_genes"] = len(known)
    context.external.setdefault("gene_annotation", {}).update(known)
    examples = [
        f"{gene}: {str((value or {}).get('name') or (value or {}).get('gene_type') or 'annotated')[:48]}"
        for gene, value in list(known.items())[:3]
    ]
    message = (
        f"Annotated {len(known)} gene(s) via {source}: " + "; ".join(examples) + "."
    )
    context.log("agent", "annotate_genes", "ok", message)
    return message


def annotate_genes_enhanced(
    context: RunContext,
    state: AgentState,
    genes: list[str] | None = None,
    use_ensembl: bool = True,
    use_uniprot: bool = False,
) -> str:
    """Enhanced gene annotation using bioservices (Ensembl + UniProt).

    Supplements basic MyGene.info annotation with:
    - Ensembl: transcript variants, chromosomal coordinates, biotype
    - UniProt: protein function, domains, disease associations

    Falls back gracefully if bioservices is not installed.
    """
    target = [str(gene) for gene in (genes or context.top_genes(12))]
    if not target:
        return "annotate_genes_enhanced skipped: no candidate genes available."

    try:
        from splicegaip.integrations import bioservices_client

        if not bioservices_client.backend_available():
            return "bioservices not installed; falling back to standard annotation."
    except Exception:
        return "bioservices integration unavailable."

    bridge = _bridge(state, context)
    if bridge.spent():
        return f"Enhanced annotation skipped: external budget exhausted ({bridge.used}/{bridge.budget})."

    results_summary: list[str] = []

    # Ensembl annotation
    if use_ensembl:
        try:
            ens_results = bioservices_client.ensembl_annotate(target, timeout=bridge.timeout)
            if ens_results:
                state.facts["ensembl_annotations"] = ens_results
                context.external.setdefault("ensembl_annotation", {}).update(ens_results)
                count = len(ens_results)
                examples = list(ens_results.keys())[:3]
                results_summary.append(f"Ensembl annotated {count} genes ({', '.join(examples)})")
        except Exception as exc:
            results_summary.append(f"Ensembl annotation failed: {exc}")

    # UniProt annotation (only for protein-coding genes)
    if use_uniprot:
        try:
            uniprot_results = bioservices_client.uniprot_annotate(target, timeout=bridge.timeout)
            if uniprot_results:
                state.facts["uniprot_annotations"] = uniprot_results
                context.external.setdefault("uniprot_annotation", {}).update(uniprot_results)
                count = len(uniprot_results)
                examples = list(uniprot_results.keys())[:3]
                results_summary.append(f"UniProt annotated {count} proteins ({', '.join(examples)})")
        except Exception as exc:
            results_summary.append(f"UniProt annotation failed: {exc}")

    if not results_summary:
        message = "Enhanced annotation returned no results."
        context.log("agent", "annotate_genes_enhanced", "skipped", message)
        return message

    message = "; ".join(results_summary)
    context.log("agent", "annotate_genes_enhanced", "ok", message)
    return message


def enrich_pathways_bioservices(
    context: RunContext,
    state: AgentState,
    use_kegg: bool = True,
    use_reactome: bool = True,
) -> str:
    """Pathway enrichment via KEGG/Reactome native APIs (not Enrichr wrapper).

    Uses bioservices to access pathway databases directly:
    - KEGG: canonical metabolic and signaling pathways
    - Reactome: curated human pathway database

    Provides alternative/complementary results to GSEApy/Enrichr.
    """
    try:
        from splicegaip.integrations import bioservices_client

        if not bioservices_client.backend_available():
            return "bioservices not installed; use standard enrichment instead."
    except Exception:
        return "bioservices integration unavailable."

    bridge = _bridge(state, context)
    if bridge.spent():
        return f"Pathway enrichment skipped: external budget exhausted ({bridge.used}/{bridge.budget})."

    genes = context.top_genes(20)
    if not genes:
        return "No candidate genes available for pathway analysis."

    results_summary: list[str] = []
    all_pathways: list[dict[str, Any]] = []

    # KEGG pathways
    if use_kegg:
        try:
            kegg_results = bioservices_client.kegg_pathways(genes, timeout=bridge.timeout * 1.5)
            if kegg_results:
                all_pathways.extend(kegg_results)
                count = len(kegg_results)
                top_terms = [pw["term"][:60] for pw in kegg_results[:3]]
                results_summary.append(f"KEGG found {count} pathways ({'; '.join(top_terms)})")
        except Exception as exc:
            results_summary.append(f"KEGG query failed: {exc}")

    # Reactome pathways
    if use_reactome:
        try:
            reactome_results = bioservices_client.reactome_pathways(genes, timeout=bridge.timeout * 1.5)
            if reactome_results:
                all_pathways.extend(reactome_results)
                count = len(reactome_results)
                top_terms = [pw["term"][:60] for pw in reactome_results[:3]]
                results_summary.append(f"Reactome found {count} pathways ({'; '.join(top_terms)})")
        except Exception as exc:
            results_summary.append(f"Reactome query failed: {exc}")

    if not all_pathways:
        message = "bioservices pathway search returned no results."
        context.log("agent", "enrich_pathways_bioservices", "skipped", message)
        return message

    # Store in context.external for report generation
    state.facts["bioservices_pathways"] = all_pathways
    context.external.setdefault("pathways", {})["bioservices_rows"] = all_pathways

    message = "; ".join(results_summary)
    context.log("agent", "enrich_pathways_bioservices", "ok", message)
    return message


def search_literature(
    context: RunContext,
    state: AgentState,
    gene: str | None = None,
    query: str | None = None,
    max_results: int = 5,
) -> str:
    """Search PubMed/Europe PMC for splicing evidence on a candidate gene."""
    bridge = _bridge(state, context)
    if not bridge.enabled:
        return "External literature search disabled (agent.skills.enabled=false)."
    if bridge.spent():
        return f"Literature search skipped: external call budget exhausted ({bridge.used}/{bridge.budget})."
    target_gene = gene or (context.top_genes(1) or [None])[0]
    if not target_gene and not query:
        return "Literature search skipped: no gene or query given."
    text = query or f"{target_gene} alternative splicing"
    from splicegaip.skills.literature_search import LiteratureSearchSkill

    result = bridge.run_skill(
        "literature_search",
        LiteratureSearchSkill,
        query=text,
        max_results=int(max_results),
        sources=["pubmed", "europe_pmc"],
        include_abstracts=False,
    )
    if result is None:
        message = f"External literature search for '{text}' returned no usable records."
        context.log("agent", "search_literature", "skipped", message)
        return message
    rows = list((result.data or {}).get("results") or [])
    added = 0
    from splicegaip.knowledge.rag import Evidence

    bucket = context.evidence.setdefault(str(target_gene or text), [])
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        meta = " ".join(
            str(row.get(key) or "") for key in ("journal", "year") if row.get(key)
        ).strip()
        bucket.append(
            Evidence(
                gene=str(target_gene or text),
                text=(f"{title} ({meta})" if meta else title)[:400],
                source=str(row.get("source") or "external"),
                pmid=str(row.get("pmid") or ""),
            )
        )
        added += 1
    context.external.setdefault("literature", {})[str(target_gene or text)] = {
        "query": text,
        "records": rows[:10],
    }
    state.facts.setdefault("external_searches", []).append(text)
    message = f"Literature search '{text}': {added} record(s) added ({len(rows)} returned)."
    context.log("agent", "search_literature", "ok", message)
    return message


def enrich_pathways(
    context: RunContext,
    state: AgentState,
    genes: list[str] | None = None,
    organism: str = "human",
    top_terms: int = 15,
) -> str:
    """Over-representation analysis through GSEApy/Enrichr (or the built-in skill)."""
    bridge = _bridge(state, context)
    if not bridge.enabled:
        return "External pathway enrichment disabled (agent.skills.enabled=false)."
    if bridge.spent():
        return f"Pathway enrichment skipped: external call budget exhausted ({bridge.used}/{bridge.budget})."
    target = [str(gene) for gene in (genes or context.top_genes(40))]
    if len(target) < 2:
        return f"Pathway enrichment skipped: only {len(target)} gene(s) available."

    rows: list[dict[str, Any]] | None = None
    source = ""
    try:
        from splicegaip.integrations import enrichr

        if enrichr.backend_available():
            rows = enrichr.enrich(
                target, organism=organism, top_terms=int(top_terms), timeout=bridge.timeout
            )
            bridge.calls.append(
                SkillCall("pathway_enrichment", {"genes": target[:8]}, "ok" if rows else "empty", "GSEApy/Enrichr")
            )
            source = "GSEApy/Enrichr"
    except Exception:  # noqa: BLE001 - optional backend
        rows = None

    if not rows:
        from splicegaip.skills.pathway_enrichment import PathwayEnrichmentSkill

        result = bridge.run_skill(
            "pathway_enrichment",
            PathwayEnrichmentSkill,
            genes=target,
            ontologies=["GO", "KEGG"],
            fdr_threshold=0.05,
        )
        if result is None:
            message = "Pathway enrichment produced no terms (external sources unavailable)."
            context.log("agent", "enrich_pathways", "skipped", message)
            return message
        data = result.data or {}
        rows = [
            {
                "term": str(item.get("term") or item.get("name") or ""),
                "library": str(item.get("ontology") or item.get("database") or "Enrichr"),
                "ontology": str(item.get("ontology") or "GO"),
                "genes": tuple(str(gene) for gene in (item.get("genes") or [])),
                "gene_count": len(item.get("genes") or []),
                "fold_enrichment": item.get("fold_enrichment"),
                "p_value": item.get("p_value"),
                "fdr": item.get("fdr"),
                "source": "PathwayEnrichmentSkill",
            }
            for item in (data.get("enriched_terms") or [])
        ]
        source = "built-in PathwayEnrichmentSkill"

    rows = [row for row in rows if row.get("term")]
    if not rows:
        message = f"Pathway enrichment via {source} returned no significant terms for {len(target)} genes."
        context.log("agent", "enrich_pathways", "empty", message)
        return message

    from splicegaip.analysis.enrichment import EnrichmentResult

    existing = {(item.term, item.ontology) for item in context.enrichment}
    added = 0
    for row in rows:
        key = (row["term"], row.get("ontology") or "Enrichr")
        if key in existing:
            continue
        context.enrichment.append(
            EnrichmentResult(
                ontology=str(row.get("ontology") or "Enrichr"),
                term=str(row["term"]),
                gene_count=int(row.get("gene_count") or 0),
                background_count=len(target),
                fold_enrichment=float(row.get("fold_enrichment") or 0.0),
                p_value=float(row.get("p_value") or 1.0),
                fdr=float(row.get("fdr") or 1.0),
                genes=tuple(row.get("genes") or ()),
            )
        )
        added += 1
    context.enrichment.sort(key=lambda item: item.fdr)
    context.external.setdefault("pathways", {})["rows"] = rows[:15]
    context.external["pathways"]["source"] = source
    state.facts["enriched_terms"] = len(context.enrichment)
    state.facts["enriched"] = True
    top = rows[0]
    message = (
        f"Pathway enrichment ({source}): {added} term(s) added, {len(context.enrichment)} total; "
        f"top: {str(top.get('term'))[:60]} (FDR={top.get('fdr')})."
    )
    context.log("agent", "enrich_pathways", "ok", message)
    return message


def _coordinates_of(event: Any) -> tuple[str | None, int | None, int | None, str | None]:
    """Best-effort parse of chromosome/start/end/strand from an event."""
    chrom = getattr(event, "chromosome", None) or None
    strand = getattr(event, "strand", None) or None
    raw = getattr(event, "genomic_coordinates", "") or ""
    match = re.search(r"(\d+)\s*[-:]\s*(\d+)", str(raw))
    start = int(match.group(1)) if match else None
    end = int(match.group(2)) if match else None
    return chrom, start, end, strand


def interpret_splice_event(
    context: RunContext,
    state: AgentState,
    gene: str | None = None,
    event_type: str | None = None,
) -> str:
    """Interpret the biological/clinical meaning of one top event."""
    bridge = _bridge(state, context)
    if not bridge.enabled:
        return "External splice interpretation disabled (agent.skills.enabled=false)."
    if bridge.spent():
        return f"Splice interpretation skipped: external call budget exhausted ({bridge.used}/{bridge.budget})."

    event = None
    if gene:
        for item in context.candidates or context.significant_events:
            if str(getattr(item, "gene_symbol", "")).lower() == str(gene).lower():
                event = item
                break
    if event is None and context.candidates:
        event = context.candidates[0]
    if event is None and context.significant_events:
        event = context.significant_events[0]
    if event is None:
        return "Splice interpretation skipped: no significant event available."

    target_gene = str(gene or getattr(event, "gene_symbol", "") or getattr(event, "gene_id", ""))
    target_type = str(event_type or getattr(event, "event_type", "") or "SE").upper()
    if not target_gene:
        return "Splice interpretation skipped: event carries no gene symbol."

    from splicegaip.skills.splice_interpretation import SpliceInterpretationSkill

    chrom, start, end, strand = _coordinates_of(event)
    result = bridge.run_skill(
        "splice_interpretation",
        SpliceInterpretationSkill,
        gene_symbol=target_gene,
        event_type=target_type,
        chromosome=chrom,
        start=start,
        end=end,
        strand=strand,
        delta_psi=getattr(event, "delta_psi", None),
        fdr=getattr(event, "fdr", None),
    )
    if result is None:
        message = f"Splice interpretation for {target_gene} ({target_type}) returned nothing."
        context.log("agent", "interpret_splice_event", "skipped", message)
        return message
    data = dict(result.data or {})
    interpretation = data.get("interpretation") or {}
    context.external.setdefault("interpretation", {})[target_gene] = {
        "event_type": target_type,
        "summary": interpretation.get("summary"),
        "protein_impact": interpretation.get("protein_impact"),
        "clinical_significance": interpretation.get("clinical_significance"),
        "therapeutic_opportunities": interpretation.get("therapeutic_opportunities"),
    }
    state.facts.setdefault("interpreted_events", []).append(f"{target_gene}:{target_type}")
    summary = str(interpretation.get("summary") or "interpretation retrieved")
    message = f"Interpreted {target_gene} ({target_type}): {summary[:240]}"
    context.log("agent", "interpret_splice_event", "ok", message)
    return message


# --------------------------------------------------------------------------
# Wrapped platform tools (existing behaviour, agent-callable)
# --------------------------------------------------------------------------


def summarize_dataset(context: RunContext, state: AgentState) -> str:
    from splicegaip.tools.data_tools import summarize_dataset as _impl

    return _impl(context)


def filter_significant_events(
    context: RunContext,
    state: AgentState,
    fdr_threshold: float | None = None,
    delta_psi_threshold: float | None = None,
    event_types: list[str] | None = None,
) -> str:
    from splicegaip.tools.analysis_tools import filter_significant_events as _impl

    fdr = fdr_threshold if fdr_threshold is not None else state.params.get("fdr")
    dpsi = delta_psi_threshold if delta_psi_threshold is not None else state.params.get("delta_psi")
    return _impl(context, fdr, dpsi, event_types)


def rank_candidates(context: RunContext, state: AgentState, top_n: int | None = None) -> str:
    from splicegaip.tools.analysis_tools import rank_candidates as _impl

    return _impl(context, top_n or state.params.get("top_n"))


def run_enrichment(context: RunContext, state: AgentState, alpha: float | None = None) -> str:
    from splicegaip.tools.analysis_tools import run_enrichment as _impl

    return _impl(context, alpha)


def generate_figures(context: RunContext, state: AgentState, output_dir: str | None = None) -> str:
    from splicegaip.tools.viz_tools import generate_figures as _impl

    return _impl(context, output_dir)


def collect_literature_evidence(
    context: RunContext,
    state: AgentState,
    genes: list[str] | None = None,
    max_per_gene: int = 2,
) -> str:
    from splicegaip.tools.knowledge_tools import collect_literature_evidence as _impl

    return _impl(context, genes, max_per_gene)


def interpret_candidates(context: RunContext, state: AgentState) -> str:
    from splicegaip.tools.knowledge_tools import interpret_candidates as _impl

    return _impl(context)


def generate_report(context: RunContext, state: AgentState, output_dir: str | None = None) -> str:
    from splicegaip.tools.report_tools import generate_report as _impl

    return _impl(context, output_dir)


def consult_knowledge(context: RunContext, state: AgentState, min_projects: int = 2) -> str:
    """Check lab-level recurrence before interpreting candidates.

    Queries the knowledge base for genes that appeared in multiple past
    projects and are also in the current candidate list. Results are stored
    in ``state.facts["recurrent_genes"]`` for downstream actions.
    """
    from .knowledge import LabKnowledge

    # Mark as checked to avoid repeated calls
    state.facts["knowledge_checked"] = True

    # Get current candidate genes
    candidates = context.candidates or []
    if not candidates:
        return "No candidates to check against knowledge base."

    candidate_genes = [
        c.gene_symbol or c.gene_id for c in candidates if (c.gene_symbol or c.gene_id)
    ]

    # Query knowledge base
    kb = LabKnowledge()
    recurrent = kb.intersect_with_candidates(candidate_genes, min_projects=min_projects)

    if recurrent:
        state.facts["recurrent_genes"] = recurrent
        gene_names = ", ".join(r["gene"] for r in recurrent[:5])
        suffix = f" and {len(recurrent) - 5} more" if len(recurrent) > 5 else ""
        return (
            f"Found {len(recurrent)} recurrent genes in knowledge base: {gene_names}{suffix}. "
            f"These genes appeared in ≥{min_projects} prior projects and may warrant extra attention."
        )
    else:
        state.facts["recurrent_genes"] = []
        stats = kb.get_stats()
        return (
            f"No recurrent genes found in knowledge base ({stats['unique_genes']} unique genes "
            f"from {stats['projects_tracked']} projects tracked). Proceeding with standard interpretation."
        )


def persist_knowledge(context: RunContext, state: AgentState, top_n: int = 10) -> str:
    """Save top candidates from this run into the knowledge base.

    This is typically called at the end of a successful analysis to enrich
    the knowledge base for future runs.
    """
    from .knowledge import KnowledgeEntry, LabKnowledge

    candidates = context.candidates or []
    if not candidates:
        return "No candidates to persist."

    entries = []
    for i, cand in enumerate(candidates[:top_n]):
        entries.append(
            KnowledgeEntry(
                gene=cand.gene_symbol or cand.gene_id,
                project_id=context.project_id,
                event_type=cand.event_type,
                delta_psi=cand.delta_psi,
                fdr=cand.fdr,
                rank=i + 1,
            )
        )

    kb = LabKnowledge()
    count = kb.add_entries(context.project_id, entries)
    return f"Persisted {count} candidate genes to lab knowledge base for future recurrence tracking."


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------


def build_registry() -> dict[str, Action]:
    """All actions the decision engine may pick from."""
    actions = [
        Action("profile_dataset", "Profile the dataset (size, missingness, quality, groups)", profile_dataset),
        Action("assess_quality", "Check how the quality gates behave at the current thresholds", assess_quality),
        Action("adapt_thresholds", "Choose FDR/dPSI thresholds from the data (balanced/strict/exploratory)", adapt_thresholds),
        Action("summarize_dataset", "Summarize the loaded dataset", summarize_dataset),
        Action("filter_significant_events", "Filter AS events by FDR and |dPSI| with quality gating", filter_significant_events),
        Action("rank_candidates", "Rank significant events by the composite score", rank_candidates, requires=("filtered", "has_significant")),
        Action("run_enrichment", "Run GO/KEGG over-representation analysis", run_enrichment, requires=("filtered",)),
        Action("generate_figures", "Generate the publication figure set", generate_figures),
        Action("collect_literature_evidence", "Collect literature evidence for candidate genes", collect_literature_evidence),
        Action("interpret_candidates", "Produce the evidence-grounded biological interpretation", interpret_candidates, requires=("filtered",)),
        Action("generate_report", "Write the HTML/PDF report", generate_report),
        Action("deep_dive_gene", "Zoom into one gene (events, effect sizes, literature)", deep_dive_gene),
        # Phase 2: self-challenge and external knowledge.
        Action(
            "test_hypothesis",
            "Statistically challenge the result (PSI shift, direction, type bias, confounds)",
            test_hypothesis,
            requires=("filtered", "has_significant"),
        ),
        Action(
            "annotate_genes",
            "Annotate candidate genes from MyGene.info / Ensembl",
            annotate_genes,
            requires=("filtered", "has_significant"),
        ),
        Action(
            "search_literature",
            "Search PubMed / Europe PMC for splicing evidence on a gene",
            search_literature,
            requires=("filtered", "has_significant"),
        ),
        Action(
            "enrich_pathways",
            "Over-representation analysis via GSEApy/Enrichr (works without a local annotation table)",
            enrich_pathways,
            requires=("filtered", "has_significant"),
        ),
        Action(
            "interpret_splice_event",
            "Interpret the clinical/functional meaning of one top splicing event",
            interpret_splice_event,
            requires=("filtered", "has_significant"),
        ),
        # Step 3: knowledge persistence
        Action(
            "consult_knowledge",
            "Check lab-level recurrence before interpreting candidates",
            consult_knowledge,
            requires=("ranked",),
        ),
        Action(
            "persist_knowledge",
            "Save top candidates into lab knowledge base for future analyses",
            persist_knowledge,
            requires=("interpreted",),
        ),
        # Step 5: bioservices enhanced capabilities
        Action(
            "annotate_genes_enhanced",
            "Enhanced annotation via Ensembl/UniProt (bioservices)",
            annotate_genes_enhanced,
            requires=("filtered", "has_significant"),
        ),
        Action(
            "enrich_pathways_bioservices",
            "Pathway enrichment via KEGG/Reactome native APIs (bioservices)",
            enrich_pathways_bioservices,
            requires=("filtered", "has_significant"),
        ),
    ]
    return {action.name: action for action in actions}
