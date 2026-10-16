"""Statistical hypothesis testing: the agent challenges its own result.

Phase 1 made the agent able to *decide* what to do; it still accepted every
result at face value. This module adds the missing scientific step: before
interpreting anything, the agent tests a small set of pre-registered
hypotheses about the numbers it just produced. Each test either supports the
result or exposes a confound, and the outcome is reported (never silently
dropped).

All tests are computed locally with :mod:`scipy` — no network, no model, and
they run identically offline.

* ``dpsi_shift``        — is the ΔPSI distribution really shifted away from 0?
* ``direction_balance`` — is the up/down direction of change symmetric?
* ``event_type_bias``   — is one event type over-represented among hits?
* ``coverage_confound`` — is effect size driven by read depth (technical bias)?
* ``gene_recurrence``   — do hits cluster in fewer genes than chance allows?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

ALPHA_DEFAULT = 0.05
#: Minimum group size before a test is considered interpretable.
MIN_N = 5


@dataclass(frozen=True)
class HypothesisResult:
    """Outcome of one pre-registered test."""

    code: str
    title: str
    method: str
    statistic: float | None
    p_value: float | None
    fdr: float | None
    effect: str
    n: int
    verdict: str  # rejected | not rejected | inconclusive
    interpretation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "method": self.method,
            "statistic": None if self.statistic is None else round(float(self.statistic), 6),
            "p_value": None if self.p_value is None else float(f"{self.p_value:.6g}"),
            "fdr": None if self.fdr is None else float(f"{self.fdr:.6g}"),
            "effect": self.effect,
            "n": self.n,
            "verdict": self.verdict,
            "interpretation": self.interpretation,
        }


def _benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """BH step-up adjusted p-values (monotone, clipped at 1)."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    previous = 1.0
    for rank, index in enumerate(reversed(order), start=1):
        position = m - rank  # 0-based index in ascending order
        value = p_values[index] * m / (position + 1)
        previous = min(previous, value)
        adjusted[index] = min(previous, 1.0)
    return adjusted


def _float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        return None if number != number else number
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# individual tests
# ---------------------------------------------------------------------------


def _test_dpsi_shift(values: list[float]) -> tuple[float | None, float | None, str]:
    """Wilcoxon signed-rank (or t-test for small n) against a zero shift."""
    import scipy.stats as stats  # noqa: PLC0415 - optional backend

    n = len(values)
    if n < MIN_N:
        return None, None, "one-sample t-test (n<10)"
    try:
        result = stats.wilcoxon(values)
        return float(result.statistic), float(result.pvalue), "Wilcoxon signed-rank vs 0"
    except Exception:  # noqa: BLE001 - all-zero ties make Wilcoxon undefined
        try:
            result = stats.ttest_1samp(values, 0.0)
            return float(result.statistic), float(result.pvalue), "one-sample t-test vs 0"
        except Exception:  # noqa: BLE001
            return None, None, "one-sample t-test vs 0"


def _test_direction_balance(up: int, down: int) -> tuple[float | None, float | None, str]:
    import scipy.stats as stats  # noqa: PLC0415

    total = up + down
    if total < MIN_N:
        return None, None, "binomial test (two-sided, p=0.5)"
    try:
        result = stats.binomtest(up, total, 0.5)
        return float(up / total), float(result.pvalue), "binomial test (two-sided, p=0.5)"
    except Exception:  # noqa: BLE001
        return None, None, "binomial test (two-sided, p=0.5)"


def _test_event_type_bias(
    hit_counts: dict[str, int], background_counts: dict[str, int]
) -> tuple[float | None, float | None, str, str]:
    """Chi-square goodness of fit of hit types against the background mix."""
    import numpy as np  # noqa: PLC0415
    import scipy.stats as stats  # noqa: PLC0415

    background_total = sum(background_counts.values())
    hit_total = sum(hit_counts.values())
    if background_total < 10 or hit_total < MIN_N:
        return None, None, "chi-square goodness of fit", ""
    types = [key for key in background_counts if background_counts[key] > 0]
    if len(types) < 2:
        return None, None, "chi-square goodness of fit", ""
    observed = np.array([hit_counts.get(key, 0) for key in types], dtype=float)
    expected_proportions = np.array(
        [background_counts[key] / background_total for key in types], dtype=float
    )
    expected = expected_proportions * hit_total
    if float(expected.min()) < 1.0:
        return None, None, "chi-square goodness of fit", ""
    try:
        result = stats.chisquare(observed, expected)
        ratio = {
            key: (hit_counts.get(key, 0) / hit_total) / (background_counts[key] / background_total)
            for key in types
        }
        top = max(ratio.items(), key=lambda item: item[1])
        effect = f"{top[0]} enriched {top[1]:.2f}x over background"
        return float(result.statistic), float(result.pvalue), "chi-square goodness of fit", effect
    except Exception:  # noqa: BLE001
        return None, None, "chi-square goodness of fit", ""


def _test_coverage_confound(
    effects: list[float], support: list[float], missing: list[float]
) -> tuple[float | None, float | None, str, str]:
    """Spearman correlation between |ΔPSI| and depth / missingness."""
    import numpy as np  # noqa: PLC0415
    import scipy.stats as stats  # noqa: PLC0415

    pairs = [
        (abs(effect), value)
        for effect, value in zip(effects, support or missing)
        if effect is not None and value is not None
    ]
    if len(pairs) < MIN_N:
        return None, None, "Spearman rank correlation", ""
    xs = np.array([item[0] for item in pairs], dtype=float)
    ys = np.array([item[1] for item in pairs], dtype=float)
    if float(np.std(xs)) == 0.0 or float(np.std(ys)) == 0.0:
        return None, None, "Spearman rank correlation", ""
    try:
        result = stats.spearmanr(xs, ys)
        rho = float(result.statistic)
        label = "support reads" if support else "PSI missing rate"
        direction = "positive" if rho > 0 else "negative"
        return rho, float(result.pvalue), "Spearman rank correlation", f"rho={rho:+.2f} vs {label} ({direction})"
    except Exception:  # noqa: BLE001
        return None, None, "Spearman rank correlation", ""


def _test_gene_recurrence(
    events_per_gene: dict[str, int], background_events_per_gene: dict[str, int]
) -> tuple[float | None, float | None, str, str]:
    """Permutation test: do hits concentrate in fewer genes than chance?"""
    import numpy as np  # noqa: PLC0415

    observed_genes = len(events_per_gene)
    hit_events = sum(events_per_gene.values())
    if observed_genes < 3 or hit_events < MIN_N:
        return None, None, "permutation test (1000 shuffles)", ""
    background_genes = [value for value in background_events_per_gene.values() if value > 0]
    if len(background_genes) < 3:
        return None, None, "permutation test (1000 shuffles)", ""
    rng = np.random.default_rng(20240517)
    weights = np.array(background_genes, dtype=float)
    weights = weights / weights.sum()
    hits = int(max(events_per_gene.values()))
    # Null: draw `hit_events` events uniformly from the background genes and
    # look at how many events land in the single most hit gene.
    draws = rng.choice(len(weights), size=(1000, hit_events), p=weights)
    null_max = np.array(
        [int(np.bincount(row, minlength=len(weights)).max()) for row in draws], dtype=float
    )
    p_value = float((null_max >= hits).sum() + 1) / (len(null_max) + 1)
    top_gene, top_count = max(events_per_gene.items(), key=lambda item: item[1])
    return (
        float(top_count),
        p_value,
        "permutation test (1000 shuffles)",
        f"{top_gene} carries {top_count} independent events",
    )


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def run_hypothesis_tests(context: Any, alpha: float = ALPHA_DEFAULT) -> list[HypothesisResult]:
    """Run every pre-registered test against the current run context."""
    significant = list(getattr(context, "significant_events", []) or [])
    all_events = list(getattr(context, "dataset", None).events if getattr(context, "dataset", None) else [])
    if not significant:
        return []

    deltas = [_float(event.delta_psi) for event in significant]
    deltas = [value for value in deltas if value is not None]
    up = sum(1 for value in deltas if value > 0)
    down = sum(1 for value in deltas if value < 0)

    hit_types: dict[str, int] = {}
    for event in significant:
        hit_types[event.event_type] = hit_types.get(event.event_type, 0) + 1
    background_types: dict[str, int] = {}
    for event in all_events:
        background_types[event.event_type] = background_types.get(event.event_type, 0) + 1

    hits_per_gene: dict[str, int] = {}
    for event in significant:
        key = event.gene_symbol or event.gene_id or "?"
        hits_per_gene[key] = hits_per_gene.get(key, 0) + 1
    background_per_gene: dict[str, int] = {}
    for event in all_events:
        key = event.gene_symbol or event.gene_id or "?"
        background_per_gene[key] = background_per_gene.get(key, 0) + 1

    support = [_float(getattr(event, "total_support_reads", None)) for event in significant]
    missing = [_float(getattr(event, "psi_missing_rate", None)) for event in significant]
    support_clean = [value for value in support if value is not None]
    missing_clean = [value for value in missing if value is not None]

    raw: list[tuple[str, str, float | None, float | None, str, str, int]] = []

    stat, p, method = _test_dpsi_shift(deltas)
    median_delta = _median(deltas)
    raw.append(
        (
            "dpsi_shift",
            "Differential splicing shifts PSI away from zero",
            stat,
            p,
            method,
            f"median ΔPSI={median_delta:+.3f}" if median_delta is not None else "no ΔPSI",
            len(deltas),
        )
    )

    stat, p, method = _test_direction_balance(up, down)
    raw.append(
        (
            "direction_balance",
            "Inclusion gains and losses are balanced",
            stat,
            p,
            method,
            f"{up} up / {down} down",
            up + down,
        )
    )

    stat, p, method, effect = _test_event_type_bias(hit_types, background_types)
    raw.append(
        (
            "event_type_bias",
            "Hit event types follow the background composition",
            stat,
            p,
            method,
            effect or "no comparison possible",
            sum(hit_types.values()),
        )
    )

    stat, p, method, effect = _test_coverage_confound(
        deltas,
        support_clean if len(support_clean) >= MIN_N else [],
        missing_clean,
    )
    raw.append(
        (
            "coverage_confound",
            "Effect size is independent of read depth",
            stat,
            p,
            method,
            effect or "no depth/missingness column available",
            max(len(support_clean), len(missing_clean)),
        )
    )

    stat, p, method, effect = _test_gene_recurrence(hits_per_gene, background_per_gene)
    raw.append(
        (
            "gene_recurrence",
            "Hits are not concentrated in a few genes",
            stat,
            p,
            method,
            effect or "no recurrence observed",
            sum(hits_per_gene.values()),
        )
    )

    p_values = [item[3] if item[3] is not None else 1.0 for item in raw]
    adjusted = _benjamini_hochberg(p_values)

    results: list[HypothesisResult] = []
    for index, (code, title, statistic, p_value, method, effect, n) in enumerate(raw):
        fdr = adjusted[index] if p_value is not None else None
        results.append(
            HypothesisResult(
                code=code,
                title=title,
                method=method,
                statistic=statistic,
                p_value=p_value,
                fdr=fdr,
                effect=effect,
                n=n,
                verdict=_verdict(p_value, fdr, n, alpha),
                interpretation=_interpret(code, p_value, fdr, effect, n, alpha),
            )
        )
    return results


def _verdict(p_value: float | None, fdr: float | None, n: int, alpha: float) -> str:
    if p_value is None or n < MIN_N:
        return "inconclusive"
    value = fdr if fdr is not None else p_value
    return "rejected" if value < alpha else "not rejected"


def _interpret(
    code: str,
    p_value: float | None,
    fdr: float | None,
    effect: str,
    n: int,
    alpha: float,
) -> str:
    if p_value is None or n < MIN_N:
        return f"Not testable with n={n}; reported as inconclusive rather than assumed."
    value = fdr if fdr is not None else p_value
    if value >= alpha:
        return (
            f"H0 retained (adjusted p={value:.3g}, n={n}); {effect}. "
            "No evidence against the assumption, so the result stands as computed."
        )
    note = {
        "dpsi_shift": "The significant set is genuinely shifted in PSI — the signal is not an artefact of the gate.",
        "direction_balance": "Direction of change is asymmetric; report the skew rather than describing a balanced switch.",
        "event_type_bias": "One event type dominates the hits — a detection-sensitivity bias must be discussed.",
        "coverage_confound": "Effect size tracks sequencing depth — treat large ΔPSI events as depth-confounded.",
        "gene_recurrence": "Independent events recur in the same genes, which strengthens those candidates.",
    }.get(code, "The null hypothesis was rejected.")
    return f"H0 rejected (adjusted p={value:.3g}, n={n}): {note} ({effect})."


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def text_summary(results: Sequence[HypothesisResult]) -> str:
    """One-line-per-test summary for logs and the workflow trace."""
    if not results:
        return "No hypothesis tests could be run (no significant events)."
    lines = []
    for item in results:
        p_text = "NA" if item.p_value is None else f"{item.p_value:.3g}"
        q_text = "NA" if item.fdr is None else f"{item.fdr:.3g}"
        lines.append(
            f"- {item.code}: {item.verdict} (p={p_text}, BH q={q_text}, n={item.n}) {item.effect}"
        )
    return "\n".join(lines)


@dataclass
class HypothesisLedger:
    """Where the agent keeps the test outcomes for the rest of the run."""

    results: list[HypothesisResult] = field(default_factory=list)
    alpha: float = ALPHA_DEFAULT

    def rejected(self) -> list[HypothesisResult]:
        return [item for item in self.results if item.verdict == "rejected"]

    def confounds(self) -> list[HypothesisResult]:
        return [
            item
            for item in self.results
            if item.verdict == "rejected" and item.code in {"coverage_confound", "event_type_bias"}
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "alpha": self.alpha,
            "tests": [item.as_dict() for item in self.results],
            "rejected": [item.code for item in self.rejected()],
            "confounds": [item.code for item in self.confounds()],
        }
