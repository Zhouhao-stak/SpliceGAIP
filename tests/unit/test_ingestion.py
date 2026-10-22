"""Tests for the agentic ingestion layer (profile -> map -> standardize)."""

from __future__ import annotations

import json

import pytest

from splicegaip.data.ingestion import apply_ingestion, apply_native_groups, preview_ingestion
from splicegaip.data.loader import load_dataset
from splicegaip.data.validator import validate_dataset

MESSY_VENDOR = """Vendor RNA Splicing Report
Generated 2026-10-21
Gene Name,Gene ID,Event Type,Chromosome,Strand,Exon Start,Exon End,PSI Control,PSI Treatment,Delta PSI,p-value,q-value,PSI_CTRL_1,PSI_CTRL_2,PSI_TRT_1,PSI_TRT_2
GeneA,ENSG000001,Exon Skipping,chr1,+,100,200,80,35,-45,0.0001,0.0002,0.82,0.78,0.36,0.34
GeneB,ENSG000002,Mutually Exclusive Exons,chr2,-,300,500,20,75,55,<0.001,0.002,0.18,0.22,0.74,0.76
"""

DECIMAL_COMMA_TSV = """Sample;Gene;Type;dPSI;p;PSI_control_1;PSI_control_2;PSI_treated_1;PSI_treated_2
S1;GENEX;Skipped exon;25,5;0,001;62,0;58,0;30,0;28,0
S2;GENEY;Intron retention;-40,0;0,02;70,0;72,0;20,0;18,0
S3;;Exon skipping;10,0;0,5;50,0;50,0;55,0;60,0
"""


def _codes(payload: dict) -> set[str]:
    return {issue["code"] for issue in payload.get("issues", [])}


def _write(tmp_path, name: str, text: str):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_preview_maps_messy_vendor_export(tmp_path):
    _write(tmp_path, "messy_vendor.csv", MESSY_VENDOR)

    data = preview_ingestion(tmp_path, use_llm=False)

    assert data["status"] == "mapped"
    assert data["mapping_source"] == "heuristic"
    assert data["confidence"]["level"] == "high"
    assert data["event_file"]["header_row"] == 2
    columns = data["mapping"]["columns"]
    assert columns["gene_symbol"] == "Gene Name"
    assert columns["delta_PSI"] == "Delta PSI"
    assert columns["FDR"] == "q-value"
    assert columns["mean_PSI_group1"] == "PSI Control"

    preview = data["preview"]
    assert preview["valid_events"] == 2
    assert preview["groups"] == {"Control": 2, "Treatment": 2}
    assert preview["event_types"] == {"SE": 1, "MXE": 1}
    assert preview["events"][0]["delta_psi"] == pytest.approx(-0.45)
    assert preview["events"][1]["fdr"] == pytest.approx(0.002)
    assert "psi_percent_scaled" in _codes(data)
    assert preview["validation"]["ok"] is True


def test_decimal_commas_and_pvalue_fdr_fallback(tmp_path):
    _write(tmp_path, "vendor.tsv", DECIMAL_COMMA_TSV)

    data = preview_ingestion(tmp_path, use_llm=False)

    preview = data["preview"]
    assert preview["valid_events"] == 2
    assert preview["dropped"] == 1
    assert preview["sample_count"] == 4
    assert preview["groups"] == {"Control": 2, "Treatment": 2}
    first = preview["events"][0]
    assert first["delta_psi"] == pytest.approx(0.255)
    assert first["p_value"] == pytest.approx(0.001)
    assert first["fdr"] == pytest.approx(0.001)
    assert {"fdr_from_p", "rows_dropped", "means_from_samples"} <= _codes(data)


def test_apply_writes_dataset_the_loader_can_read(tmp_path):
    _write(tmp_path, "messy_vendor.csv", MESSY_VENDOR)
    data = preview_ingestion(tmp_path, use_llm=False)

    result = apply_ingestion(tmp_path, data["mapping"])

    output = tmp_path / "standardized"
    assert result["path"] == str(output)
    assert (output / "AS_event_master.csv").is_file()
    assert (output / "sample_metadata.csv").is_file()
    mapping_file = json.loads((output / "ingestion_mapping.json").read_text(encoding="utf-8"))
    assert "api_key" not in json.dumps(mapping_file).lower()

    dataset = load_dataset(output)
    assert dataset.source_format == "standard"
    assert dataset.summary()["event_count"] == 2
    assert dataset.groups == {"Control": ["CTRL_1", "CTRL_2"], "Treatment": ["TRT_1", "TRT_2"]}
    validation = validate_dataset(dataset)
    assert validation.ok
    assert not validation.warnings


def test_native_standard_table_skips_mapping(tmp_path):
    _write(
        tmp_path,
        "AS_event_master.csv",
        "event_id,gene_id,gene_symbol,event_type,chromosome,strand,"
        "genomic_coordinates,coordinate_system,source_tool,mean_PSI_group1,"
        "mean_PSI_group2,delta_PSI,p_value,FDR\n"
        "E1,G1,GENE1,SE,chr1,+,100-200,1-based,test,0.8,0.3,0.5,0.001,0.01\n",
    )
    _write(tmp_path, "sample_metadata.csv", "sample_id,group\nS1,control\nS2,treated\n")

    data = preview_ingestion(tmp_path, use_llm=False)

    assert data["native"] is True
    assert data["status"] == "native"
    assert data["mapping"] == {}
    assert data["validation"]["ok"] is True


def test_confirmed_groups_create_sample_metadata_for_unlabeled_samples(tmp_path):
    _write(tmp_path, "vendor.csv", "Gene,Type,Delta PSI,p,PSI_S1,PSI_S2,PSI_S3,PSI_S4\n"
           "A,SE,0.4,0.001,0.2,0.3,0.7,0.8\n")
    preview = preview_ingestion(tmp_path, use_llm=False)
    assert preview["sample_ids"] == ["S1", "S2", "S3", "S4"]
    assert preview["preview"]["sample_count"] == 0
    mapping = preview["mapping"]
    mapping["sample_groups"] = {"S1": "Baseline", "S2": "Baseline", "S3": "Drug", "S4": "Drug"}
    mapping["sample_groups_confirmed"] = True
    result = apply_ingestion(tmp_path, mapping)
    dataset = load_dataset(result["path"])
    assert dataset.groups == {"Baseline": ["S1", "S2"], "Drug": ["S3", "S4"]}
    assert dataset.events[0].psi_by_sample["S4"] == pytest.approx(0.8)
    from splicegaip.analysis.visualization import plot_psi_distribution, plot_psi_heatmap

    figures = tmp_path / "figures"
    heatmap = plot_psi_heatmap(dataset.events, dataset.samples, figures)
    boxes = plot_psi_distribution(dataset.events, dataset.samples, figures)
    assert (figures / "psi_heatmap.png").is_file()
    assert (figures / "psi_distribution.png").is_file()
    assert "No per-sample" not in heatmap.caption
    assert "No PSI values" not in boxes.caption


def test_native_group_confirmation_is_persisted(tmp_path):
    _write(tmp_path, "AS_event_master.csv", "event_id,gene_id,gene_symbol,event_type,delta_PSI,FDR,PSI_S1,PSI_S2\n"
           "E1,G1,GENE1,SE,0.4,0.001,0.2,0.8\n")
    preview = preview_ingestion(tmp_path, use_llm=False)
    assert preview["native"] is True
    assert preview["sample_ids"] == ["S1", "S2"]
    with pytest.raises(ValueError):
        apply_native_groups(tmp_path, {"S1": "A", "S2": "A"})
    apply_native_groups(tmp_path, {"S1": "A", "S2": "B"})
    assert load_dataset(tmp_path).groups == {"A": ["S1"], "B": ["S2"]}


def test_unmappable_directory_reports_error_and_apply_refuses(tmp_path):
    _write(tmp_path, "notes.csv", "author,comment\nAlice,hello\nBob,hello\n")

    data = preview_ingestion(tmp_path, use_llm=False)

    assert data["status"] == "unmappable"
    assert "no_tables" in _codes(data) or any(
        issue["severity"] == "error" for issue in data["issues"]
    )
    with pytest.raises(ValueError):
        apply_ingestion(tmp_path, data["mapping"])


class _FakeEnhancer:
    errors: list[dict[str, str]] = []

    def __init__(self, proposal):
        self.proposal = proposal

    def has(self, feature: str) -> bool:
        return feature == "ingest"

    def json(self, **kwargs):
        return self.proposal


def test_llm_proposal_is_accepted_only_after_header_validation(tmp_path):
    _write(tmp_path, "messy_vendor.csv", MESSY_VENDOR)
    good = _FakeEnhancer(
        {
            "event_file": "messy_vendor.csv",
            "columns": {
                "gene_symbol": "Gene Name",
                "delta_PSI": "Delta PSI",
                "FDR": "q-value",
                "event_type": "Event Type",
            },
            "confidence": 0.93,
            "notes": ["vendor export"],
        }
    )

    data = preview_ingestion(tmp_path, enhancer=good)

    assert data["mapping_source"] == "llm+heuristic"
    assert data["llm"]["used"] is True
    assert data["mapping"]["columns"]["gene_symbol"] == "Gene Name"
    assert data["status"] == "mapped"


def test_hallucinated_llm_mapping_falls_back_to_heuristic(tmp_path):
    _write(tmp_path, "messy_vendor.csv", MESSY_VENDOR)
    bad = _FakeEnhancer(
        {
            "event_file": "not_a_real_file.csv",
            "columns": {"gene_symbol": "Imaginary Column", "delta_PSI": "Also Missing"},
            "confidence": 0.99,
        }
    )

    data = preview_ingestion(tmp_path, enhancer=bad)

    assert data["mapping_source"] == "heuristic"
    assert data["llm"]["used"] is False
    assert data["mapping"]["event_file"] == "messy_vendor.csv"
    assert data["mapping"]["columns"]["gene_symbol"] == "Gene Name"
    assert data["preview"]["valid_events"] == 2


def test_llm_group_proposal_uses_only_observed_samples(tmp_path):
    _write(tmp_path, "vendor.csv", "Gene,Type,Delta PSI,p,PSI_S1,PSI_S2\nA,SE,0.4,0.001,0.2,0.8\n")
    proposal = _FakeEnhancer({"sample_groups": {"S1": "Before", "S2": "After", "S999": "Invented"}})
    data = preview_ingestion(tmp_path, enhancer=proposal)
    assert data["mapping"]["sample_groups"] == {"S1": "Before", "S2": "After"}
    assert data["preview"]["groups"] == {"Before": 1, "After": 1}
    assert data["llm"]["used"] is True


def test_native_llm_group_suggestion_is_reviewable(tmp_path):
    _write(tmp_path, "AS_event_master.csv", "event_id,gene_id,gene_symbol,event_type,delta_PSI,FDR,PSI_S1,PSI_S2\n"
           "E1,G1,GENE1,SE,0.4,0.001,0.2,0.8\n")
    data = preview_ingestion(tmp_path, enhancer=_FakeEnhancer({"sample_groups": {"S1": "A", "S2": "B", "S3": "C"}}))
    assert data["mapping"]["sample_groups"] == {"S1": "A", "S2": "B"}
    assert data["sample_ids"] == ["S1", "S2"]
