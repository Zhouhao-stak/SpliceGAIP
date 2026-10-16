"""Domain-level LLM tasks for SpliceGAIP.

Each function turns a deterministic result into a model-enriched result.
Every one of them is failure-tolerant: on any problem (no credentials,
timeout, malformed JSON, hallucinated keys) the deterministic input is
returned unchanged and the failure is recorded on the enhancer.

The prompts deliberately carry *only computed facts*. The model is
instructed to rewrite, summarise and hypothesise from those facts — never
to invent numbers, genes or citations.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Mapping, Sequence

from splicegaip.llm.enrich import ALL_FEATURES, LLMEnhancer, detect_language

LANG_HINT = {
    "zh": "请用简体中文输出，术语（基因名、PSI、FDR、GO/KEGG）保留英文原文。",
    "en": "Answer in English.",
}

MAX_NARRATIVE_PARAGRAPHS = 6
MAX_LIST_ITEMS = 8

_SYSTEM_BASE = (
    "You are a computational biology assistant embedded in SpliceGAIP, an "
    "alternative-splicing analysis platform. You are given computed results "
    "as JSON. You may rephrase, summarise, prioritise and hypothesise from "
    "them, but you must NEVER invent numbers, gene names, pathways or "
    "citations that are not present in the input. Statistical results are "
    "facts; biological mechanisms you add are hypotheses and must be labelled "
    "as such. Never claim clinical utility or causality."
)


def _lang(query: str, configured: str) -> str:
    return detect_language(query, configured)


def _hint(language: str) -> str:
    return LANG_HINT.get(language, LANG_HINT["en"])


def _strings(value: Any, limit: int = MAX_LIST_ITEMS, max_len: int = 400) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, (str, int, float)):
            text = str(item).strip()
        elif isinstance(item, Mapping):
            text = json.dumps(item, ensure_ascii=False)
        else:
            continue
        if text:
            out.append(text[:max_len])
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# fact extraction
# ---------------------------------------------------------------------------
def context_facts(context: Any, *, max_candidates: int = 12, max_terms: int = 10) -> dict[str, Any]:
    """Compact, JSON-serialisable fact sheet for one run."""
    dataset = context.dataset
    analysis = context.settings.analysis
    groups = {str(group): len(ids) for group, ids in (dataset.groups or {}).items()}
    return {
        "project_id": context.project_id,
        "query": context.query,
        "dataset": dataset.name,
        "source_format": dataset.source_format,
        "samples": len(dataset.samples),
        "groups": groups,
        "events": len(dataset.events),
        "significant_events": len(context.significant_events),
        "candidates": len(context.candidates),
        "enriched_terms": len(context.enrichment),
        "annotated_genes": len(dataset.annotation or {}),
        "figures": [figure.name for figure in context.figures],
        "thresholds": {
            "fdr": analysis.fdr_threshold,
            "delta_psi": analysis.delta_psi_threshold,
            "min_support_reads": analysis.min_support_reads,
            "min_valid_samples": analysis.min_valid_samples,
            "top_candidates": analysis.top_candidates,
        },
        "top_candidates": [
            {
                "gene": item.gene_symbol or item.gene_id,
                "event_type": item.event_type,
                "delta_psi": item.delta_psi,
                "fdr": item.fdr,
                "score": round(item.score, 3),
            }
            for item in context.candidates[:max_candidates]
        ],
        "top_enrichment": [
            {
                "term": item.term,
                "ontology": item.ontology,
                "genes": item.gene_count,
                "fold": round(item.fold_enrichment, 2),
                "fdr": item.fdr,
            }
            for item in context.enrichment[:max_terms]
        ],
        "evidence_genes": sorted(gene for gene, entries in (context.evidence or {}).items() if entries),
        "validation_warnings": (
            [issue.message for issue in context.validation.warnings[:5]]
            if context.validation is not None
            else []
        ),
    }


def evidence_digest(context: Any, *, per_gene: int = 2) -> dict[str, list[str]]:
    """Map gene -> list of evidence texts (trimmed)."""
    digest: dict[str, list[str]] = {}
    for gene, entries in (context.evidence or {}).items():
        texts = [str(entry.text)[:300] for entry in entries[:per_gene] if getattr(entry, "text", "")]
        if texts:
            digest[gene] = texts
    return digest


# ---------------------------------------------------------------------------
# 1. query / intent understanding
# ---------------------------------------------------------------------------
def understand_query(
    query: str,
    *,
    settings: Any = None,
    enhancer: LLMEnhancer | None = None,
    facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Turn a natural-language question into a structured analysis intent.

    Falls back to the rule-based classifier when no model is available.
    """
    from splicegaip.agents.policy import classify_query

    analysis_type, goal = classify_query(query)
    baseline: dict[str, Any] = {
        "goal": goal,
        "analysis_type": analysis_type,
        "assumptions": [],
        "suggested_thresholds": {},
        "focus_genes": [],
        "source": "rule",
    }
    if enhancer is None:
        if settings is None:
            return baseline
        enhancer = LLMEnhancer(settings)
    if not enhancer.has("understand"):
        return baseline
    language = _lang(query, enhancer.settings.llm.language)
    payload = {
        "user_query": query,
        "dataset": {key: facts[key] for key in ("source_format", "events", "samples", "groups") if facts and key in facts}
        or None,
        "rule_baseline": {"analysis_type": analysis_type, "goal": goal},
        "allowed_analysis_types": ["differential_AS", "DE_analysis", "combined", "exploration"],
    }
    system = (
        _SYSTEM_BASE
        + " You classify the user's research intent and propose analysis parameters. "
        + _hint(language)
    )
    user = (
        "Analyse the request below and reply with JSON only:\n"
        '{"goal": "<one sentence>", "analysis_type": "<one of allowed_analysis_types>", '
        '"assumptions": ["..."], "suggested_thresholds": {"fdr": <number|null>, '
        '"delta_psi": <number|null>, "top_candidates": <int|null>}, '
        '"focus_genes": ["<gene symbols mentioned by the user, else empty>"]}\n\n'
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    parsed = enhancer.json(system=system, user=user, feature="understand", max_tokens=600)
    if not isinstance(parsed, dict):
        return baseline
    merged = dict(baseline)
    merged["goal"] = str(parsed.get("goal") or goal)[:400]
    candidate_type = str(parsed.get("analysis_type") or "")
    if candidate_type in {"differential_AS", "DE_analysis", "combined", "exploration"}:
        merged["analysis_type"] = candidate_type
    merged["assumptions"] = _strings(parsed.get("assumptions"), limit=5)
    merged["focus_genes"] = _strings(parsed.get("focus_genes"), limit=20, max_len=40)
    suggested = parsed.get("suggested_thresholds")
    if isinstance(suggested, Mapping):
        clean: dict[str, Any] = {}
        for key in ("fdr", "delta_psi"):
            value = suggested.get(key)
            if isinstance(value, (int, float)) and 0 < float(value) < 1:
                clean[key] = float(value)
        value = suggested.get("top_candidates")
        if isinstance(value, int) and 0 < value <= 200:
            clean["top_candidates"] = value
        merged["suggested_thresholds"] = clean
    merged["source"] = "llm"
    return merged


def classify_query_fallback(query: str, error: str = "") -> dict[str, Any]:
    """Rule-based intent baseline (used when the model path is unavailable)."""
    from splicegaip.agents.policy import classify_query

    analysis_type, goal = classify_query(query)
    payload: dict[str, Any] = {
        "goal": goal,
        "analysis_type": analysis_type,
        "assumptions": [],
        "suggested_thresholds": {},
        "focus_genes": [],
        "source": "rule",
    }
    if error:
        payload["error"] = str(error)[:200]
    return payload


# ---------------------------------------------------------------------------
# 2. planner refinement
# ---------------------------------------------------------------------------
def enhance_plan(
    enhancer: LLMEnhancer,
    *,
    query: str,
    facts: Mapping[str, Any],
    base_plan: Mapping[str, Any],
    language: str = "en",
) -> dict[str, Any]:
    """Refine the deterministic plan (goal wording + limitations)."""
    plan = dict(base_plan or {})
    plan.setdefault("source", "deterministic")
    if not enhancer.has("plan"):
        return plan
    system = (
        _SYSTEM_BASE
        + " You refine an analysis plan for an alternative-splicing study. "
        + _hint(language)
    )
    user = (
        "Refine the plan below using the dataset facts. Reply with JSON only:\n"
        '{"goal": "<one sentence>", "potential_limitations": ["..."], '
        '"expected_outputs": ["..."]}\n\n'
        f"query: {query}\n"
        f"facts: {json.dumps(facts, ensure_ascii=False, indent=2)}\n"
        f"plan: {json.dumps(base_plan, ensure_ascii=False, indent=2)}"
    )
    parsed = enhancer.json(system=system, user=user, feature="plan", max_tokens=700)
    if not isinstance(parsed, dict):
        return plan
    goal = str(parsed.get("goal") or "").strip()
    if goal:
        plan["goal"] = goal[:400]
    limitations = _strings(parsed.get("potential_limitations"), limit=MAX_LIST_ITEMS)
    if limitations:
        plan["potential_limitations"] = limitations
    outputs = _strings(parsed.get("expected_outputs"), limit=MAX_LIST_ITEMS)
    if outputs:
        plan["expected_outputs"] = outputs
    plan["source"] = "llm"
    return plan


# ---------------------------------------------------------------------------
# 3. narrative interpretation
# ---------------------------------------------------------------------------
def narrate(
    enhancer: LLMEnhancer,
    *,
    query: str,
    facts: Mapping[str, Any],
    deterministic: str,
    evidence: Mapping[str, Sequence[str]] | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Write the narrative interpretation on top of the deterministic text."""
    if not enhancer.has("interpret"):
        return {"source": "deterministic", "lead": "", "paragraphs": [], "highlights": []}
    system = (
        _SYSTEM_BASE
        + " You write the biological interpretation section of a scientific "
        "report about differential alternative splicing. Keep every number "
        "identical to the input. Separate established statistical findings "
        "from hypotheses explicitly. "
        + _hint(language)
    )
    user = (
        "Write the interpretation. Reply with JSON only:\n"
        '{"lead": "<one sentence headline finding>", "paragraphs": ["<paragraph>", ...], '
        '"highlights": ["<bullet>", ...]}\n'
        f"- at most {MAX_NARRATIVE_PARAGRAPHS} paragraphs, 2-4 sentences each;\n"
        "- at most 5 highlight bullets, each a single takeaway;\n"
        "- label any mechanistic or therapeutic suggestion as a hypothesis.\n\n"
        f"user query: {query}\n"
        f"facts: {json.dumps(facts, ensure_ascii=False, indent=2)}\n"
        f"deterministic interpretation: {deterministic}\n"
        f"literature evidence: {json.dumps(evidence or {}, ensure_ascii=False, indent=2)}"
    )
    parsed = enhancer.json(system=system, user=user, feature="interpret", max_tokens=1400)
    if not isinstance(parsed, dict):
        return {"source": "deterministic", "lead": "", "paragraphs": [], "highlights": []}
    lead = str(parsed.get("lead") or "").strip()
    paragraphs = _strings(parsed.get("paragraphs"), limit=MAX_NARRATIVE_PARAGRAPHS, max_len=1200)
    highlights = _strings(parsed.get("highlights"), limit=5, max_len=240)
    if not (lead or paragraphs or highlights):
        return {"source": "deterministic", "lead": "", "paragraphs": [], "highlights": []}
    return {"source": "llm", "lead": lead[:400], "paragraphs": paragraphs, "highlights": highlights}


# ---------------------------------------------------------------------------
# 4. per-gene biological annotation
# ---------------------------------------------------------------------------
def annotate_genes(
    enhancer: LLMEnhancer,
    genes: Sequence[str],
    *,
    facts: Mapping[str, Any],
    language: str = "en",
) -> dict[str, str]:
    """Short biological note per candidate gene (batched into one call)."""
    if not enhancer.has("annotate") or not genes:
        return {}
    wanted = [gene for gene in genes if gene][: enhancer.max_genes]
    if not wanted:
        return {}
    system = (
        _SYSTEM_BASE
        + " You write one concise biological annotation per gene, in the "
        "context of alternative splicing and disease. "
        + _hint(language)
    )
    user = (
        "Reply with JSON only, mapping every requested gene to one annotation "
        "of at most 45 words: {\"<gene>\": \"<annotation>\"}. "
        "The annotation must state the gene's biological role and, when it is "
        "plausible, why an isoform switch could matter; phrase mechanistic "
        "possibilities as hypotheses. Do not invent citations.\n\n"
        f"genes: {json.dumps(wanted, ensure_ascii=False)}\n"
        f"study context: {json.dumps({k: facts.get(k) for k in ('query', 'groups', 'source_format', 'top_candidates')}, ensure_ascii=False, indent=2)}"
    )
    parsed = enhancer.json(system=system, user=user, feature="annotate", max_tokens=1200)
    if not isinstance(parsed, dict):
        return {}
    notes: dict[str, str] = {}
    for gene in wanted:
        value = parsed.get(gene) or parsed.get(str(gene).upper()) or parsed.get(str(gene).lower())
        if isinstance(value, str) and value.strip():
            notes[gene] = value.strip()[:400]
    return notes


# ---------------------------------------------------------------------------
# 5. literature evidence summarisation
# ---------------------------------------------------------------------------
def summarize_evidence(
    enhancer: LLMEnhancer,
    evidence: Mapping[str, Sequence[str]],
    *,
    language: str = "en",
) -> dict[str, str]:
    """One evidence-grounded sentence per gene with literature records."""
    if not enhancer.has("literature") or not evidence:
        return {}
    genes = [gene for gene in evidence if gene][: enhancer.max_genes]
    if not genes:
        return {}
    payload = {gene: list(evidence[gene])[:3] for gene in genes}
    system = (
        _SYSTEM_BASE
        + " You summarise retrieved literature records. Use ONLY the supplied "
        "records; if they are weak, say the support is limited. "
        + _hint(language)
    )
    user = (
        "Reply with JSON only, one summary per gene (at most 60 words): "
        "{\"<gene>\": \"<summary>\"}. Every summary must stay traceable to the "
        "supplied records and must not add facts that are not in them.\n\n"
        f"records: {json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    parsed = enhancer.json(system=system, user=user, feature="literature", max_tokens=1200)
    if not isinstance(parsed, dict):
        return {}
    summaries: dict[str, str] = {}
    for gene in genes:
        value = parsed.get(gene)
        if isinstance(value, str) and value.strip():
            summaries[gene] = value.strip()[:500]
    return summaries


# ---------------------------------------------------------------------------
# 6. limitations
# ---------------------------------------------------------------------------
def extend_limitations(
    enhancer: LLMEnhancer,
    base: Sequence[str],
    *,
    facts: Mapping[str, Any],
    language: str = "en",
) -> list[str]:
    """Add study-design limitations that follow from the supplied facts."""
    baseline = [str(item) for item in base if str(item).strip()]
    if not enhancer.has("limitations"):
        return baseline
    system = (
        _SYSTEM_BASE
        + " You list additional methodological limitations of an "
        "alternative-splicing analysis. Only use facts you were given. "
        + _hint(language)
    )
    user = (
        "Reply with JSON only: {\"limitations\": [\"...\"]} with at most 5 new "
        "limitations (<= 30 words each) that are NOT already in the list below "
        "and that follow from the dataset facts (sample size, single-omic "
        "design, PSI estimation, multiple testing, annotation coverage, lack of "
        "validation cohort, etc.).\n\n"
        f"existing: {json.dumps(baseline, ensure_ascii=False)}\n"
        f"facts: {json.dumps(facts, ensure_ascii=False, indent=2)}"
    )
    parsed = enhancer.json(system=system, user=user, feature="limitations", max_tokens=700)
    items: list[str] = []
    if isinstance(parsed, Mapping):
        items = _strings(parsed.get("limitations"), limit=5, max_len=240)
    elif isinstance(parsed, list):
        items = _strings(parsed, limit=5, max_len=240)
    merged = list(baseline)
    for item in items:
        if item not in merged:
            merged.append(item)
    return merged


# ---------------------------------------------------------------------------
# 7. hypotheses + validation plan
# ---------------------------------------------------------------------------
def hypothesize(
    enhancer: LLMEnhancer,
    *,
    facts: Mapping[str, Any],
    language: str = "en",
) -> dict[str, Any]:
    """Generate hypotheses, validation experiments and follow-up analyses."""
    empty = {"hypotheses": [], "validations": [], "followups": [], "source": "none"}
    if not enhancer.has("hypotheses"):
        return empty
    system = (
        _SYSTEM_BASE
        + " You propose testable hypotheses and a validation plan. Everything "
        "you propose must be explicitly a hypothesis or a recommendation. "
        + _hint(language)
    )
    user = (
        "Reply with JSON only:\n"
        '{"hypotheses": ["..."], "validations": ["..."], "followups": ["..."]}\n'
        "- hypotheses: at most 4, each testable and tied to a specific gene or "
        "pathway from the results;\n"
        "- validations: at most 4, concrete experimental or computational "
        "checks (RT-PCR, minigene assay, RNA-seq validation cohort, ...);\n"
        "- followups: at most 4, next analyses on the same data.\n\n"
        f"facts: {json.dumps(facts, ensure_ascii=False, indent=2)}"
    )
    parsed = enhancer.json(system=system, user=user, feature="hypotheses", max_tokens=900)
    if not isinstance(parsed, Mapping):
        return empty
    return {
        "hypotheses": _strings(parsed.get("hypotheses"), limit=4),
        "validations": _strings(parsed.get("validations"), limit=4),
        "followups": _strings(parsed.get("followups"), limit=4),
        "source": "llm",
    }


# ---------------------------------------------------------------------------
# 8. critique
# ---------------------------------------------------------------------------
def critique(
    enhancer: LLMEnhancer,
    narrative: Mapping[str, Any],
    *,
    facts: Mapping[str, Any],
    deterministic: str,
    language: str = "en",
) -> dict[str, Any]:
    """Second-model pass checking the narrative for unsupported claims."""
    if not enhancer.has("critique") or not narrative:
        return {"issues": [], "verdict": "", "source": "none"}
    system = (
        _SYSTEM_BASE
        + " You are the critic. You check a draft interpretation against the "
        "computed facts and flag unsupported or overstated claims. "
        + _hint(language)
    )
    user = (
        "Reply with JSON only: {\"verdict\": \"<one sentence>\", \"issues\": "
        "[\"...\"]}. List at most 4 issues; each issue must name a number, gene "
        "or claim that is missing, wrong or overstated. If the draft is faithful, "
        "return an empty issues list and say so in the verdict.\n\n"
        f"facts: {json.dumps(facts, ensure_ascii=False, indent=2)}\n"
        f"deterministic interpretation: {deterministic}\n"
        f"draft: {json.dumps(narrative, ensure_ascii=False, indent=2)}"
    )
    parsed = enhancer.json(
        system=system,
        user=user,
        feature="critique",
        model=enhancer.critic_model,
        max_tokens=700,
        temperature=0.0,
    )
    if not isinstance(parsed, Mapping):
        return {"issues": [], "verdict": "", "source": "none"}
    return {
        "issues": _strings(parsed.get("issues"), limit=4, max_len=300),
        "verdict": str(parsed.get("verdict") or "")[:300],
        "source": "llm",
    }


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def enrich_context(context: Any, *, enhancer: LLMEnhancer | None = None) -> dict[str, Any]:
    """Run every enabled enrichment for one run and store it on the context.

    Returns the insights dictionary (also assigned to
    ``context.llm_insights``). Safe to call in deterministic mode: it then
    returns a status-only payload.
    """
    enhancer = enhancer or LLMEnhancer(
        context.settings,
        logger=lambda agent, action, status, detail: context.log(agent, action, status, detail),
    )
    language = _lang(context.query, enhancer.settings.llm.language)
    insights: dict[str, Any] = {
        "enabled": enhancer.enabled,
        "language": language,
        "model": enhancer.model,
        "features": sorted(enhancer.features),
        "available_features": list(ALL_FEATURES),
        "status": enhancer.describe(),
        "sections": {},
    }
    if not enhancer.enabled:
        insights["note"] = (
            "未配置大模型端点（MODEL_API_BASE_URL / MODEL_API_KEY / MODEL_NAME），"
            "本次运行使用确定性分析策略，结果与有模型时完全一致。"
        )
        context.llm_insights = insights
        return insights

    try:
        facts = context_facts(context)
        digest = evidence_digest(context)

        # Reuse the pre-run understanding (same prompt -> cache hit anyway).
        cached = getattr(context, "understanding", None)
        if isinstance(cached, dict) and cached.get("source") == "llm":
            understanding = cached
        else:
            understanding = understand_query(context.query, enhancer=enhancer, facts=facts)
        insights["understanding"] = understanding
        context.understanding = understanding

        # Keep the deterministic plan as the contract; only wording and
        # limitations are replaced by the model.
        base_plan = dict(context.plan or {}) or None
        if base_plan:
            insights["plan"] = enhance_plan(
                enhancer, query=context.query, facts=facts, base_plan=base_plan, language=language
            )
            context.plan = insights["plan"]

        from splicegaip.report.generator import build_interpretation

        deterministic_text = build_interpretation(context)

        narrative = narrate(
            enhancer,
            query=context.query,
            facts=facts,
            deterministic=deterministic_text,
            evidence=digest,
            language=language,
        )
        insights["narrative"] = narrative

        genes = [item.gene_symbol or item.gene_id for item in context.candidates]
        insights["gene_notes"] = annotate_genes(enhancer, genes, facts=facts, language=language)
        insights["evidence_summaries"] = summarize_evidence(enhancer, digest, language=language)

        if narrative.get("paragraphs") or narrative.get("lead"):
            insights["critique"] = critique(
                enhancer,
                narrative,
                facts=facts,
                deterministic=deterministic_text,
                language=language,
            )

        insights["hypotheses"] = hypothesize(enhancer, facts=facts, language=language)

        from splicegaip.report.generator import ReportGenerator

        base_limitations = ReportGenerator(context)._limitations()  # noqa: SLF001
        insights["limitations"] = extend_limitations(
            enhancer, base_limitations, facts=facts, language=language
        )
    except Exception as error:  # noqa: BLE001 - enrichment must never break a run
        insights["errors"] = list(enhancer.errors) + [{"feature": "enrich_context", "error": str(error)}]
        try:
            context.log("llm", "enrich_context", "error", str(error)[:400])
        except Exception:  # noqa: BLE001
            pass
    finally:
        insights["status"] = enhancer.describe()
        insights["calls"] = len(enhancer.calls)
        insights["errors"] = list(enhancer.errors)

    context.llm_insights = insights
    return insights
