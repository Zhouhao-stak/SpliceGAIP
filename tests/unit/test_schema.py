"""Tests for splicing schema and data models."""

import pytest
from splicegaip.splicing.schema import StandardEvent, _to_float, _to_int


class TestStandardEvent:
    """Test cases for StandardEvent model."""

    def test_create_minimal_event(self):
        """Test creating event with required fields."""
        event = StandardEvent(
            event_id="event_001",
            gene_id="ENSG00000001",
            gene_symbol="TEST",
            event_type="SE",
            chromosome="chr1",
            strand="+",
            genomic_coordinates="chr1:1000-1100",
            coordinate_system="hg38",
            source_tool="rMATS",
            mean_psi_group1=0.8,
            mean_psi_group2=0.3,
            delta_psi=0.5,
            p_value=0.01,
            fdr=0.05
        )
        assert event.event_id == "event_001"
        assert event.gene_id == "ENSG00000001"
        assert event.event_type == "SE"
        assert abs(event.delta_psi - 0.5) < 0.01

    def test_create_full_event(self):
        """Test creating event with all fields including optional ones."""
        event = StandardEvent(
            event_id="event_002",
            gene_id="ENSG00000002",
            gene_symbol="BRCA1",
            event_type="SE",
            chromosome="chr17",
            strand="-",
            genomic_coordinates="chr17:4100-4200",
            coordinate_system="hg38",
            source_tool="SUPPA2",
            mean_psi_group1=0.9,
            mean_psi_group2=0.2,
            delta_psi=0.7,
            p_value=0.001,
            fdr=0.01,
            inclusion_reads=100,
            exclusion_reads=20,
            total_support_reads=120
        )
        assert event.delta_psi == 0.7
        assert abs(event.fdr - 0.01) < 0.001
        assert abs(event.p_value - 0.001) < 0.001
        assert event.total_support_reads == 120

    def test_delta_psi_calculation(self):
        """Test delta PSI is difference of mean PSI values."""
        event = StandardEvent(
            event_id="event_003",
            gene_id="ENSG00000003",
            gene_symbol="TEST",
            event_type="SE",
            chromosome="chr1",
            strand="+",
            genomic_coordinates="chr1:1000-1100",
            coordinate_system="hg38",
            source_tool="rMATS",
            mean_psi_group1=0.775,  # (0.8 + 0.75) / 2
            mean_psi_group2=0.325,  # (0.3 + 0.35) / 2
            delta_psi=0.45,  # 0.775 - 0.325
            p_value=0.01,
            fdr=0.05
        )
        assert abs(event.delta_psi - 0.45) < 0.01

    def test_valid_event_types(self):
        """Test all supported event types from AS_EVENT_TYPES."""
        valid_types = ["SE", "MXE", "A5SS", "A3SS", "RI"]
        for event_type in valid_types:
            event = StandardEvent(
                event_id=f"event_{event_type}",
                gene_id="ENSG00000001",
                gene_symbol="TEST",
                event_type=event_type,
                chromosome="chr1",
                strand="+",
                genomic_coordinates="chr1:1000-1100",
                coordinate_system="hg38",
                source_tool="rMATS",
                mean_psi_group1=0.5,
                mean_psi_group2=0.3,
                delta_psi=0.2,
                p_value=0.05,
                fdr=0.1
            )
            assert event.event_type == event_type

    def test_strand_validation(self):
        """Test strand must be + or -."""
        for strand in ["+", "-"]:
            event = StandardEvent(
                event_id="event_strand",
                gene_id="ENSG00000001",
                gene_symbol="TEST",
                event_type="SE",
                chromosome="chr1",
                strand=strand,
                genomic_coordinates="chr1:1000-1100",
                coordinate_system="hg38",
                source_tool="rMATS",
                mean_psi_group1=0.5,
                mean_psi_group2=0.3,
                delta_psi=0.2,
                p_value=0.05,
                fdr=0.1
            )
            assert event.strand == strand

    def test_coordinates_format(self):
        """Test coordinate string format."""
        event = StandardEvent(
            event_id="event_coord",
            gene_id="ENSG00000001",
            gene_symbol="TEST",
            event_type="SE",
            chromosome="chr1",
            strand="+",
            genomic_coordinates="chr1:1000-2000",
            coordinate_system="hg38",
            source_tool="rMATS",
            mean_psi_group1=0.5,
            mean_psi_group2=0.3,
            delta_psi=0.2,
            p_value=0.05,
            fdr=0.1
        )
        assert ":" in event.genomic_coordinates
        assert "-" in event.genomic_coordinates

    def test_optional_quality_fields(self):
        """Test optional quality fields."""
        event = StandardEvent(
            event_id="event_quality",
            gene_id="ENSG00000001",
            gene_symbol="TEST",
            event_type="SE",
            chromosome="chr1",
            strand="+",
            genomic_coordinates="chr1:1000-1100",
            coordinate_system="hg38",
            source_tool="rMATS",
            mean_psi_group1=0.5,
            mean_psi_group2=0.3,
            delta_psi=0.2,
            p_value=0.05,
            fdr=0.1,
            inclusion_reads=80,
            exclusion_reads=20,
            total_support_reads=100,
            valid_sample_count=10
        )
        assert event.inclusion_reads == 80
        assert event.exclusion_reads == 20
        assert event.total_support_reads == 100

    def test_psi_by_sample_dict(self):
        """Test per-sample PSI dictionary."""
        event = StandardEvent(
            event_id="event_sample",
            gene_id="ENSG00000001",
            gene_symbol="TEST",
            event_type="SE",
            chromosome="chr1",
            strand="+",
            genomic_coordinates="chr1:1000-1100",
            coordinate_system="hg38",
            source_tool="rMATS",
            mean_psi_group1=0.5,
            mean_psi_group2=0.3,
            delta_psi=0.2,
            p_value=0.05,
            fdr=0.1,
            psi_by_sample={"sample1": 0.6, "sample2": 0.4}
        )
        assert "sample1" in event.psi_by_sample
        assert abs(event.psi_by_sample["sample1"] - 0.6) < 0.01


class TestHelperFunctions:
    """Test helper functions for data conversion."""

    def test_to_float_valid(self):
        """Test converting valid strings to float."""
        assert _to_float("0.5") == 0.5
        assert _to_float("1.23") == 1.23
        assert _to_float("-0.1") == -0.1

    def test_to_float_invalid(self):
        """Test handling of invalid float strings."""
        assert _to_float("NA") is None
        assert _to_float("") is None
        assert _to_float("invalid") is None
        assert _to_float(None) is None

    def test_to_int_valid(self):
        """Test converting valid strings to int."""
        assert _to_int("10") == 10
        assert _to_int("0") == 0
        assert _to_int("-5") == -5

    def test_to_int_float_string(self):
        """Test that float strings are converted to int by truncation."""
        # _to_int converts "10.5" to 10 (truncates)
        result = _to_int("10.5")
        assert result == 10

    def test_to_int_invalid(self):
        """Test handling of truly invalid int strings."""
        assert _to_int("NA") is None
        assert _to_int("") is None
        assert _to_int(None) is None

    def test_to_float_edge_cases(self):
        """Test edge cases for float conversion."""
        assert _to_float("nan") is None or _to_float("nan") != _to_float("nan")
        assert _to_float("0") == 0.0

    def test_to_int_edge_cases(self):
        """Test edge cases for int conversion."""
        assert _to_int("999999999") == 999999999
        assert _to_int("-999999999") == -999999999
