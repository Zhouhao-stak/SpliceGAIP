"""Tests for the autonomous agent's pure state, profile, and reflection logic."""

from pathlib import Path
from types import SimpleNamespace

from splicegaip.agent.profile import build_profile, profile_text
from splicegaip.agent.reflector import MAX_RETRIES, reflect, remediate
from splicegaip.agent.state import (
    BLOCKER,
    INFO,
    WARNING,
    AgentState,
    Goal,
    Issue,
    StepRecord,
    default_criteria,
)
from splicegaip.data.loader import Dataset
from splicegaip.splicing.schema import SampleMetadata, StandardEvent


def _event(event_id: str = "E1", **overrides) -> StandardEvent:
    values = {
        "event_id": event_id,
        "gene_id": "G1",
        "gene_symbol": "GENE1",
        "event_type": "SE",
        "chromosome": "chr1",
        "strand": "+",
        "genomic_coordinates": "100-200",
        "coordinate_system": "1-based",
        "source_tool": "test",
        "mean_psi_group1": 0.8,
        "mean_psi_group2": 0.3,
        "delta_psi": 0.5,
        "p_value": 0.001,
        "fdr": 0.01,
        "total_support_reads": 50,
    }
    values.update(overrides)
    return StandardEvent(**values)


def _dataset(*, events=None, samples=None, annotation=None) -> Dataset:
    return Dataset(
        name="demo",
        source_dir=Path("."),
        source_format="standard",
        events=list(events or [_event()]),
        samples=list(samples or []),
        annotation=dict(annotation or {}),
    )


def _context(dataset: Dataset):
    return SimpleNamespace(
        dataset=dataset,
        significant_events=[],
        candidates=[],
        enrichment=[],
        figures=[],
        evidence={},
        report_paths={},
        filter_report=None,
    )


def test_profile_reports_quality_flags_and_text():
    dataset = _dataset(
        events=[_event(total_support_reads=10, fdr=None, delta_psi=None)],
        samples=[SampleMetadata("S1", "control"), SampleMetadata("S2", "treated")],
    )
    profile = build_profile(_context(dataset))

    assert profile["event_count"] == 1
    assert profile["groups"] == {"control": 1, "treated": 1}
    assert profile["fdr_coverage"] == 0.0
    assert profile["delta_psi_coverage"] == 0.0
    assert {"small_dataset", "sparse_fdr", "sparse_delta_psi", "low_support_reads"} <= set(
        profile["flags"]
    )
    assert "Profile: 1 events" in profile_text(profile)


def test_profile_detects_imbalanced_groups_and_missing_metadata():
    samples = [SampleMetadata("C1", "control")] + [
        SampleMetadata(f"T{i}", "treated") for i in range(1, 4)
    ]
    profile = build_profile(_context(_dataset(samples=samples)))

    assert profile["group_imbalance"] == 3.0
    assert "imbalanced_groups" in profile["flags"]
    assert "no_annotation" in profile["flags"]

    no_samples = build_profile(_context(_dataset(samples=[])))
    assert "no_sample_metadata" in no_samples["flags"]


def test_agent_state_observes_context_and_evaluates_default_goal():
    dataset = _dataset(samples=[SampleMetadata("S1", "control")])
    context = _context(dataset)
    state = AgentState(context=context, goal=Goal("splicing", "Analyze splicing"))
    state.profile = {"event_count": 1}
    state.steps.append(
        StepRecord(1, "interpret_candidates", {}, "ok", "done", "because", "rule", 0.1)
    )
    context.report_paths = {"html": Path("report.html")}
    facts = state.observe()

    assert facts["events_total"] == 1
    assert facts["profiled"] is True
    assert facts["interpreted"] is True
    assert facts["reported"] is True
    satisfied, unmet = state.goal.evaluate(state)
    assert not satisfied
    assert {"filtered", "ranked", "figures"} <= set(unmet)


def test_agent_state_helpers_sort_and_snapshot_without_mutation():
    state = AgentState(context=_context(_dataset()), goal=Goal("x", "y"))
    state.issues = [
        Issue("info", INFO, "informational"),
        Issue("block", BLOCKER, "blocking"),
        Issue("warn", WARNING, "warning"),
    ]
    state.note_action("rank_candidates")
    state.params["fdr"] = 0.05
    state.iteration = 2

    assert [item.code for item in state.sorted_issues()] == ["block", "warn", "info"]
    assert state.count_of("rank_candidates") == 1
    snapshot = state.snapshot()
    assert snapshot["iteration"] == 2
    assert snapshot["params"] == {"fdr": 0.05}
    state.resolve_issue("warn")
    assert not state.has_issue("warn")


def test_step_record_and_issue_serialization_are_bounded():
    issue = Issue("x", WARNING, "message", "try again")
    record = StepRecord(1, "act", {"x": 1}, "ok", "z" * 700, "why", "test", 1.23456)

    assert issue.as_dict()["suggestion"] == "try again"
    assert len(record.as_dict()["message"]) == 600
    assert record.as_dict()["seconds"] == 1.235


def test_reflector_maps_issues_and_honors_retry_caps():
    state = AgentState(context=_context(_dataset()), goal=Goal("x", "y"))
    state.issues = [
        Issue("no_candidates", WARNING, "none"),
        Issue("no_significant_events", WARNING, "none"),
        Issue("unknown", INFO, "ignored"),
    ]
    proposals = reflect(state)
    assert [proposal.action for proposal in proposals] == ["rank_candidates", "adapt_thresholds"]
    assert remediate("unknown", state) is None

    state.action_counts["adapt_thresholds"] = MAX_RETRIES["adapt_thresholds"]
    state.action_counts["rank_candidates"] = MAX_RETRIES["rank_candidates"]
    assert remediate("no_significant_events", state) is None
    assert remediate("no_candidates", state) is None
