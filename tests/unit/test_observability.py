"""Tests for request-safe logging configuration."""

import json
import logging

from splicegaip.observability import configure_logging


def test_configure_logging_writes_structured_event_without_secrets(tmp_path):
    log_path = tmp_path / "logs" / "splicegaip.log"
    configure_logging(log_path=log_path, level="INFO")

    logger = logging.getLogger("tests.observability")
    logger.info("analysis_started", extra={"event": "analysis_started"})
    for handler in logging.getLogger().handlers:
        handler.flush()

    record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert record["level"] == "INFO"
    assert record["message"] == "analysis_started"
    assert record["event"] == "analysis_started"
    assert "api_key" not in record


def test_configure_logging_rejects_unknown_level(tmp_path):
    log_path = tmp_path / "splicegaip.log"
    configure_logging(log_path=log_path, level="not-a-level")

    assert logging.getLogger().level == logging.INFO
