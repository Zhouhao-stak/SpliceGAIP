"""Pytest configuration and shared fixtures."""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_rmats_data():
    """Sample rMATS data for testing."""
    return """ID\tGeneID\tgeneSymbol\tchr\tstrand\texonStart_0base\texonEnd\tupstreamES\tupstreamEE\tdownstreamES\tdownstreamEE\tID\tIncFormLen\tSkipFormLen\tJCEC_Sample1\tJCEC_Sample2\tPValue\tFDR\tIncLevel1\tIncLevel2\tIncLevelDifference
1\tENSG00000000001\tTEST_GENE1\tchr1\t+\t1000\t1100\t900\t950\t1200\t1250\t1\t50\t100\t10,12\t5,6\t0.01\t0.05\t0.8,0.75\t0.3,0.35\t0.45"""


@pytest.fixture
def sample_suppa_data():
    """Sample SUPPA2 data for testing."""
    return """seqname\tstart\tend\ttotal_counts\tpsi_sample1\tpsi_sample2
chr1\t1000\t1100\t50\t0.8\t0.3
chr1\t2000\t2100\t30\t0.6\t0.7"""


@pytest.fixture
def test_config_dict():
    """Test configuration dictionary."""
    return {
        "llm": {
            "enabled": False,
            "provider": "test",
            "model": "test-model"
        },
        "analysis": {
            "fdr_threshold": 0.05,
            "delta_psi_threshold": 0.1,
            "min_support_reads": 10
        },
        "agent": {
            "mode": "scripted",
            "max_steps": 5
        }
    }
