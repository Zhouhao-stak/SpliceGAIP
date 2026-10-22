"""Small, dependency-free observability helpers for the HTTP service."""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "splicegaip_request_id", default="-"
)


def new_request_id(value: str | None = None) -> str:
    """Return a bounded, safe correlation id for one request."""
    candidate = (value or "").strip()
    if candidate and len(candidate) <= 128 and all(
        character.isalnum() or character in "._:-" for character in candidate
    ):
        return candidate
    return uuid.uuid4().hex


class _JsonFormatter(logging.Formatter):
    """Emit stable JSON fields without serialising arbitrary request data."""

    _reserved = set(logging.LogRecord(None, 0, "", 0, "", (), None).__dict__)
    _sensitive = {"api_key", "authorization", "password", "token", "secret"}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": REQUEST_ID.get(),
        }
        for key, value in record.__dict__.items():
            if key in self._reserved or key.startswith("_"):
                continue
            if any(word in key.lower() for word in self._sensitive):
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _level(value: str | int | None) -> int:
    if isinstance(value, int):
        return value
    raw = str(value or os.getenv("SPLICEGAIP_LOG_LEVEL", "INFO")).upper()
    resolved = logging.getLevelName(raw)
    return resolved if isinstance(resolved, int) else logging.INFO


def configure_logging(
    log_path: str | Path | None = None,
    level: str | int | None = None,
) -> Path:
    """Configure JSON console and rotating-file logging once per process."""
    target = Path(log_path or Path("runtime") / "logs" / "splicegaip.log").resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    formatter = _JsonFormatter()
    root = logging.getLogger()
    root.setLevel(_level(level))

    matching_file = False
    for handler in list(root.handlers):
        if not getattr(handler, "_splicegaip_file_handler", False):
            continue
        if Path(getattr(handler, "baseFilename", "")).resolve() == target:
            matching_file = True
            handler.setFormatter(formatter)
        else:
            root.removeHandler(handler)
            handler.close()

    if not matching_file:
        file_handler = logging.handlers.RotatingFileHandler(
            target, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler._splicegaip_file_handler = True  # type: ignore[attr-defined]
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if not any(
        getattr(handler, "_splicegaip_console_handler", False)
        for handler in root.handlers
    ):
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler._splicegaip_console_handler = True  # type: ignore[attr-defined]
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
    return target


def set_request_id(value: str) -> contextvars.Token[str]:
    """Bind a request id to the current async context."""
    return REQUEST_ID.set(value)


def reset_request_id(token: contextvars.Token[str]) -> None:
    """Restore the previous request id after a request finishes."""
    REQUEST_ID.reset(token)
