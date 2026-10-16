"""Run an optional backend with a hard wall-clock timeout.

Optional third-party calls have no built-in timeout we can trust (and some
block on DNS for a long time), so every call is executed on a worker thread
and abandoned if it overruns. The thread is a daemon: a stuck call can never
prevent the process from exiting.
"""

from __future__ import annotations

import concurrent.futures
from typing import Any, Callable, TypeVar

T = TypeVar("T")

_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="splicegaip-integration"
)


def run_with_timeout(func: Callable[[], T], timeout: float) -> T | None:
    """Execute ``func`` on a worker thread; return ``None`` on timeout/error."""
    try:
        future = _EXECUTOR.submit(func)
        return future.result(timeout=max(float(timeout), 0.1))
    except concurrent.futures.TimeoutError:
        return None
    except Exception:  # noqa: BLE001 - optional backends must never raise
        return None


def _rows_from_frame(frame: Any, limit: int) -> list[dict[str, Any]]:
    """Normalise a pandas DataFrame into plain dict rows (defensive)."""
    try:
        import pandas as pd  # noqa: PLC0415 - optional at this layer

        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return []
        subset = frame.head(limit)
        return [
            {str(key): _scalar(value) for key, value in row.items()}
            for row in subset.to_dict(orient="records")
        ]
    except Exception:  # noqa: BLE001
        return []


def _scalar(value: Any) -> Any:
    try:
        import math

        if value is None:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        if hasattr(value, "item"):  # numpy scalar
            return value.item()
        return value
    except Exception:  # noqa: BLE001
        return str(value)
