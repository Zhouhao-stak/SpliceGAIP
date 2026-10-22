"""Tests for input loading, validation, and significance filtering."""

from pathlib import Path

import pytest

from splicegaip.data.loader import Dataset, load_dataset, load_differential_expression
from splicegaip.data.validator import validate_dataset
from splicegaip.splicing.filtering import FilterSettings, filter_significant_events
from splicegaip.splicing.schema import SampleMetadata, StandardEvent


def _event(**overrides):
    values = {
        "event_id": "E1",
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
        "valid_sample_count": 4,
    }
    values.update(overrides)
    return StandardEvent(**values)


def test_loader_reads_standard_directory_and_metadata(tmp_path):
    (tmp_path / "AS_event_master.tsv").write_text(
        "event_id\tgene_id\tgene_symbol\tevent_type\tchromosome\tstrand\t"
        "genomic_coordinates\tcoordinate_system\tsource_tool\tmean_PSI_group1\t"
        "mean_PSI_group2\tdelta_PSI\tp_value\tFDR\n"
        "E1\tG1\tGENE1\tSE\tchr1\t+\t100-200\t1-based\ttest\t0.8\t0.3\t0.5\t0.001\t0.01\n",
        encoding="utf-8",
    )
    (tmp_path / "sample_metadata.tsv").write_text(
        "sample_id\tgroup\nS1\tcontrol\nS2\ttreated\n", encoding="utf-8"
    )

    dataset = load_dataset(tmp_path)

    assert dataset.source_format == "standard"
    assert dataset.summary()["event_count"] == 1
    assert dataset.groups == {"control": ["S1"], "treated": ["S2"]}
    assert dataset.group_labels == ("control", "treated")


def test_loader_reads_numbered_bgi_standard_export(tmp_path):
    header = (
        "event_id,gene_id,gene_symbol,event_type,chromosome,strand,"
        "genomic_coordinates,coordinate_system,source_tool,mean_PSI_group1,"
        "mean_PSI_group2,delta_PSI,p_value,FDR\n"
    )
    (tmp_path / "01_sample_metadata.csv").write_text(
        "sample_id,group\nS1,pilot_A\nS2,pilot_B\n", encoding="utf-8"
    )
    (tmp_path / "10_AS_event_master_all.csv").write_text(
        header + "E1,G1,GENE1,SE,chr1,+,100-200,1-based,BGI,0.8,0.3,0.5,0.001,0.01\n",
        encoding="utf-8",
    )

    dataset = load_dataset(tmp_path)

    assert dataset.source_format == "standard"
    assert dataset.summary()["event_count"] == 1
    assert dataset.groups == {"pilot_A": ["S1"], "pilot_B": ["S2"]}


def test_loader_detects_standard_table_by_header(tmp_path):
    (tmp_path / "vendor_export_2026.csv").write_text(
        "event_id,gene_id,gene_symbol,event_type,chromosome,strand,"
        "genomic_coordinates,coordinate_system,source_tool,mean_PSI_group1,"
        "mean_PSI_group2,delta_PSI,p_value,FDR\n"
        "E1,G1,GENE1,SE,chr1,+,100-200,1-based,vendor,0.8,0.3,0.5,0.001,0.01\n",
        encoding="utf-8",
    )

    dataset = load_dataset(tmp_path)

    assert dataset.source_format == "standard"
    assert dataset.summary()["event_count"] == 1


def test_loader_rejects_missing_or_unrecognised_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "missing")

    with pytest.raises(ValueError, match="No recognizable AS data"):
        load_dataset(tmp_path)


def test_loader_reads_csv_differential_expression(tmp_path):
    path = tmp_path / "de_results.csv"
    path.write_text(
        "gene_id,log2FC,pvalue,padj,baseMean\nG1,1.5,0.01,0.02,100\n"
        "G2,NA,,nan,50\n",
        encoding="utf-8",
    )

    genes = load_differential_expression(path)

    assert [gene.gene_id for gene in genes] == ["G1", "G2"]
    assert genes[0].log2fc == 1.5
    assert genes[1].pvalue is None


def test_validator_reports_structural_and_quality_findings():
    dataset = Dataset(
        name="bad",
        source_dir=Path("."),
        source_format="standard",
        events=[
            _event(event_id="", gene_id="", gene_symbol="", fdr=None),
            _event(event_id="", event_type="unknown", mean_psi_group1=1.2, fdr=None),
        ],
        samples=[SampleMetadata("S1", "control")],
    )

    result = validate_dataset(dataset)
    codes = {issue.code for issue in result.issues}

    assert not result.ok
    assert {"missing_event_id", "missing_gene", "duplicate_event_id", "single_group"} <= codes
    assert {"unknown_event_type", "no_fdr", "psi_out_of_range"} <= codes


def test_validator_accepts_well_formed_dataset():
    dataset = Dataset(
        name="good",
        source_dir=Path("."),
        source_format="standard",
        events=[_event()],
        samples=[SampleMetadata("S1", "control"), SampleMetadata("S2", "treated")],
    )

    result = validate_dataset(dataset)

    assert result.ok
    assert result.issues == []


def test_filter_report_tracks_significance_and_quality_reasons():
    events = [
        _event(event_id="kept"),
        _event(event_id="fdr", fdr=0.05),
        _event(event_id="reads", total_support_reads=1),
        _event(event_id="single", single_sample_driven=True),
        _event(event_id="ambiguous", mapping_ambiguity=True),
        _event(event_id="samples", valid_sample_count=1),
        _event(event_id="missing", delta_psi=None),
    ]

    kept, report = filter_significant_events(
        events, FilterSettings(fdr_threshold=0.05, delta_psi_threshold=0.1)
    )

    assert [event.event_id for event in kept] == ["kept"]
    assert report.input_count == 7
    assert report.output_count == 1
    assert report.excluded == {
        "not_significant": 2,
        "low_support_reads": 1,
        "single_sample_driven": 1,
        "mapping_ambiguity": 1,
        "insufficient_valid_samples": 1,
    }
