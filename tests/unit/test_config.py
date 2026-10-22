"""Tests for configuration management."""

import pytest
import os
from pathlib import Path
from splicegaip.config import Settings, ConfigError, load_settings


class TestSettings:
    """Test cases for Settings class."""

    def test_load_default_settings(self):
        """Test loading default settings."""
        settings = load_settings()
        assert settings is not None
        assert hasattr(settings, 'llm')
        assert hasattr(settings, 'analysis')
        assert hasattr(settings, 'agent')

    def test_analysis_thresholds(self):
        """Test analysis threshold defaults."""
        settings = load_settings()
        assert settings.analysis.fdr_threshold == 0.05
        assert settings.analysis.delta_psi_threshold == 0.1
        assert settings.analysis.min_support_reads == 10

    def test_agent_mode(self):
        """Test agent mode configuration."""
        settings = load_settings()
        assert settings.agent.mode in ['agentic', 'scripted']
        assert settings.agent.max_steps > 0
        assert settings.agent.max_seconds > 0

    def test_llm_disabled_via_env(self):
        """Test LLM can be disabled via environment variable."""
        os.environ['SPLICEGAIP_LLM_ENABLED'] = 'false'
        try:
            settings = load_settings()
            assert settings.llm.enabled is False
        finally:
            if 'SPLICEGAIP_LLM_ENABLED' in os.environ:
                del os.environ['SPLICEGAIP_LLM_ENABLED']

    def test_settings_from_yaml(self, tmp_path):
        """Test loading settings from YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
llm:
  enabled: false
  provider: test
  model: test-model

analysis:
  fdr_threshold: 0.01
  delta_psi_threshold: 0.2

agent:
  mode: scripted
  max_steps: 10
""")

        settings = load_settings(config_file)
        assert settings.llm.enabled is False
        assert settings.analysis.fdr_threshold == 0.01
        assert settings.agent.mode == 'scripted'
        assert settings.agent.max_steps == 10

    def test_invalid_config_file(self):
        """Test handling of invalid config file path."""
        from splicegaip.config import ConfigError
        with pytest.raises(ConfigError):
            load_settings(Path("/nonexistent/path/config.yaml"))

    def test_environment_override_not_applied_by_default(self):
        """Test that environment variables are checked but not always applied."""
        # This test verifies the basic loading works
        settings = load_settings()
        # Default value should be present
        assert settings.analysis.fdr_threshold == 0.05

    def test_budget_limits(self):
        """Test LLM call budget configuration."""
        settings = load_settings()
        assert settings.llm.max_calls_per_run > 0
        assert settings.llm.insight_timeout_seconds > 0


class TestSettingsValidation:
    """Test settings validation."""

    def test_valid_fdr_threshold(self):
        """Test FDR threshold must be between 0 and 1."""
        settings = load_settings()
        assert 0.0 < settings.analysis.fdr_threshold <= 1.0

    def test_valid_delta_psi(self):
        """Test delta PSI threshold must be between 0 and 1."""
        settings = load_settings()
        assert 0.0 <= settings.analysis.delta_psi_threshold <= 1.0

    def test_positive_max_steps(self):
        """Test max steps must be positive."""
        settings = load_settings()
        assert settings.agent.max_steps > 0

    def test_positive_timeout(self):
        """Test timeout must be positive."""
        settings = load_settings()
        assert settings.llm.insight_timeout_seconds > 0


class TestLLMSettings:
    """Test LLM-specific settings."""

    def test_llm_provider_options(self):
        """Test LLM provider configuration."""
        settings = load_settings()
        # Provider should be a valid string
        assert isinstance(settings.llm.provider, str)

    def test_thinking_mode(self):
        """Test thinking mode configuration."""
        settings = load_settings()
        # Thinking should be auto/disabled/enabled
        assert settings.llm.thinking in ['auto', 'disabled', 'enabled']
