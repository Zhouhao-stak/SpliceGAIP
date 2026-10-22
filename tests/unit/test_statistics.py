"""Tests for statistical analysis modules."""

import pytest
import math
from splicegaip.analysis.statistics import chi_square_p_value, benjamini_hochberg


class TestChiSquareTest:
    """Test cases for chi-square statistical test."""

    def test_significant_difference(self):
        """Test detection of significant difference in junction counts."""
        # Strong signal: high inclusion in control, low in experiment
        p_value = chi_square_p_value(
            control_in=100,
            control_out=20,
            experiment_in=30,
            experiment_out=90
        )

        assert p_value is not None
        assert 0.0 <= p_value <= 1.0
        assert p_value < 0.05  # Should be significant

    def test_no_difference(self):
        """Test when there's no significant difference."""
        # Similar ratios in both conditions
        p_value = chi_square_p_value(
            control_in=50,
            control_out=50,
            experiment_in=48,
            experiment_out=52
        )

        assert p_value is not None
        assert p_value > 0.05  # Should not be significant

    def test_zero_counts(self):
        """Test handling of zero counts (undefined test)."""
        p_value = chi_square_p_value(
            control_in=0,
            control_out=0,
            experiment_in=0,
            experiment_out=0
        )

        assert p_value is None

    def test_one_condition_zero(self):
        """Test when one condition has all zeros."""
        p_value = chi_square_p_value(
            control_in=50,
            control_out=50,
            experiment_in=0,
            experiment_out=0
        )

        assert p_value is None

    def test_edge_case_small_counts(self):
        """Test with very small counts."""
        p_value = chi_square_p_value(
            control_in=1,
            control_out=1,
            experiment_in=1,
            experiment_out=1
        )

        assert p_value is not None
        assert 0.0 <= p_value <= 1.0

    def test_large_counts(self):
        """Test with large count values."""
        p_value = chi_square_p_value(
            control_in=10000,
            control_out=2000,
            experiment_in=3000,
            experiment_out=9000
        )

        assert p_value is not None
        assert p_value < 0.001  # Should be highly significant


class TestBenjaminiHochberg:
    """Test cases for BH FDR adjustment."""

    def test_basic_adjustment(self):
        """Test basic FDR adjustment on known p-values."""
        p_values = [0.01, 0.05, 0.1, 0.5]
        adjusted = benjamini_hochberg(p_values)

        assert len(adjusted) == 4
        # All should be valid probabilities
        for adj in adjusted:
            assert adj is not None
            assert 0.0 <= adj <= 1.0
        # Adjusted values should be >= original
        for orig, adj in zip(p_values, adjusted):
            if adj is not None:
                assert adj >= orig or abs(adj - orig) < 0.001

    def test_with_none_values(self):
        """Test handling of None p-values."""
        p_values = [0.01, None, 0.05, None, 0.1]
        adjusted = benjamini_hochberg(p_values)

        assert len(adjusted) == 5
        assert adjusted[1] is None
        assert adjusted[3] is None
        # Non-None values should be adjusted
        assert adjusted[0] is not None
        assert adjusted[2] is not None
        assert adjusted[4] is not None

    def test_empty_list(self):
        """Test with empty input."""
        adjusted = benjamini_hochberg([])
        assert adjusted == []

    def test_single_value(self):
        """Test with single p-value."""
        adjusted = benjamini_hochberg([0.05])
        assert len(adjusted) == 1
        assert adjusted[0] is not None
        assert adjusted[0] >= 0.05

    def test_all_none(self):
        """Test when all values are None."""
        adjusted = benjamini_hochberg([None, None, None])
        assert adjusted == [None, None, None]

    def test_monotonicity(self):
        """Test that adjusted p-values maintain monotonicity."""
        p_values = [0.001, 0.01, 0.05, 0.1, 0.5]
        adjusted = benjamini_hochberg(p_values)

        # Filter out None values for comparison
        valid_adjusted = [adj for adj in adjusted if adj is not None]

        # Each adjusted value should be <= next (monotonicity property)
        for i in range(len(valid_adjusted) - 1):
            assert valid_adjusted[i] <= valid_adjusted[i + 1] + 0.001
