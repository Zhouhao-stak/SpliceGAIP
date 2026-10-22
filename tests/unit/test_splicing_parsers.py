"""Tests for splicing event parsers (rMATS, SUPPA2)."""

import pytest
from pathlib import Path
from splicegaip.splicing.parsers.rmats import parse_rmats_file
from splicegaip.splicing.parsers.suppa import parse_suppa_psi_file


class TestRmatsParser:
    """Test cases for rMATS parser."""

    def test_parse_se_events(self, tmp_path):
        """Test parsing SE (Skipped Exon) events from rMATS output."""
        # Create a temporary test file
        test_file = tmp_path / "SE.MATS.JC.txt"
        test_file.write_text(
            "ID\tGeneID\tgeneSymbol\tchr\tstrand\texonStart_0base\texonEnd\t"
            "upstreamES\tupstreamEE\tdownstreamES\tdownstreamEE\tID\t"
            "IncFormLen\tSkipFormLen\tIJC_SAMPLE_1\tIJC_SAMPLE_2\tSJC_SAMPLE_1\tSJC_SAMPLE_2\tPValue\tFDR\t"
            "IncLevel1\tIncLevel2\tIncLevelDifference\n"
            "1\tENSG00000000001\tTEST_GENE1\tchr1\t+\t1000\t1100\t900\t950\t"
            "1200\t1250\t1\t50\t100\t10,12\t5,6\t3,4\t2,3\t0.01\t0.05\t0.8,0.75\t0.3,0.35\t0.45\n"
        )

        result = parse_rmats_file(
            str(test_file), 
            event_type="SE",
            group1_samples=["sample1"],
            group2_samples=["sample2"]
        )

        assert len(result) == 1
        event = result[0]
        assert event.gene_id == "ENSG00000000001"
        assert event.gene_symbol == "TEST_GENE1"
        assert event.chromosome == "chr1"
        assert event.event_type == "SE"
        # delta_psi = mean(group2) - mean(group1) = 0.325 - 0.775 = -0.45
        assert event.delta_psi is not None
        assert abs(event.fdr - 0.05) < 0.01

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty rMATS file."""
        test_file = tmp_path / "empty.MATS.JC.txt"
        test_file.write_text("")

        result = parse_rmats_file(
            str(test_file),
            event_type="SE",
            group1_samples=["sample1"],
            group2_samples=["sample2"]
        )

        assert len(result) == 0

    def test_parse_invalid_format(self, tmp_path):
        """Test handling of invalid rMATS format."""
        test_file = tmp_path / "invalid.MATS.JC.txt"
        test_file.write_text("invalid content\nno proper columns")

        # Should handle gracefully without crashing
        result = parse_rmats_file(
            str(test_file),
            event_type="SE",
            group1_samples=["sample1"],
            group2_samples=["sample2"]
        )
        assert isinstance(result, list)

    def test_coordinate_extraction(self, tmp_path):
        """Test genomic coordinate extraction."""
        test_file = tmp_path / "SE.MATS.JC.txt"
        test_file.write_text(
            "ID\tGeneID\tgeneSymbol\tchr\tstrand\texonStart_0base\texonEnd\t"
            "upstreamES\tupstreamEE\tdownstreamES\tdownstreamEE\tID\t"
            "IncFormLen\tSkipFormLen\tIJC_SAMPLE_1\tIJC_SAMPLE_2\tSJC_SAMPLE_1\tSJC_SAMPLE_2\tPValue\tFDR\t"
            "IncLevel1\tIncLevel2\tIncLevelDifference\n"
            "1\tENSG00000000001\tTEST_GENE\tchr1\t+\t1000\t1100\t900\t950\t"
            "1200\t1250\t1\t50\t100\t10\t5\t3\t2\t0.01\t0.05\t0.8\t0.3\t0.5\n"
        )

        result = parse_rmats_file(
            str(test_file),
            event_type="SE",
            group1_samples=["sample1"],
            group2_samples=["sample2"]
        )

        assert len(result) == 1
        assert result[0].genomic_coordinates is not None
        assert "chr1" in result[0].genomic_coordinates


class TestSuppaParser:
    """Test cases for SUPPA2 parser."""

    def test_parse_psi_events(self, tmp_path):
        """Test parsing PSI values from SUPPA2 output."""
        test_file = tmp_path / "psi_events.txt"
        test_file.write_text(
            "seqname\tstart\tend\ttotal_counts\tpsi_sample1\tpsi_sample2\n"
            "chr1\t1000\t1100\t50\t0.8\t0.3\n"
            "chr1\t2000\t2100\t30\t0.6\t0.7\n"
        )

        result = parse_suppa_psi_file(str(test_file))

        assert len(result) == 2
        event = result[0]
        # Check that we got events back with sample PSI data
        assert event is not None
        assert len(event.psi_by_sample) > 0
        # Verify sample PSI values are stored
        assert "psi_sample1" in event.psi_by_sample
        assert abs(event.psi_by_sample["psi_sample1"] - 0.8) < 0.01

    def test_parse_missing_values(self, tmp_path):
        """Test handling of missing PSI values."""
        test_file = tmp_path / "psi_missing.txt"
        test_file.write_text(
            "seqname\tstart\tend\ttotal_counts\tpsi_sample1\tpsi_sample2\n"
            "chr1\t1000\t1100\tNA\t0.8\tNA\n"
        )

        result = parse_suppa_psi_file(str(test_file))

        # Should handle NA values gracefully
        assert isinstance(result, list)

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty SUPPA2 file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        result = parse_suppa_psi_file(str(test_file))

        assert len(result) == 0