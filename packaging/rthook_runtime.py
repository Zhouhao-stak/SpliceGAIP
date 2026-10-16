"""PyInstaller runtime hook for SpliceGAIP.

Runs before any application code when the frozen executable starts. Its only
job: make the app write runtime state (SQLite memory, project outputs) next to
the executable instead of the ephemeral PyInstaller bundle directory, which
may be read-only and is wiped on exit in onefile mode.

Users can still override with SPLICEGAIP_RUNTIME_ROOT (setdefault keeps an
explicit value).
"""

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    try:
        exe_dir = Path(sys.executable).resolve().parent
        os.environ.setdefault(
            "SPLICEGAIP_RUNTIME_ROOT", str(exe_dir / "splicegaip_runtime")
        )
        # A cache dir for matplotlib font caches (keeps %USERPROFILE% clean
        # and avoids failures on read-only profiles).
        os.environ.setdefault("MPLCONFIGDIR", str(exe_dir / "splicegaip_runtime" / ".mplcache"))
    except Exception:  # noqa: BLE001 - never block app startup over this
        pass
