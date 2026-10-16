"""Local ``.env`` read/write helpers (used to configure the model endpoint).

Credentials are never stored in reports, config YAML or the archive
database — only in a ``.env`` file next to the executable / project root,
which is exactly the file this module maintains.

The writer is deliberately conservative: it edits values *in place* so the
comments in the shipped ``.env.example`` survive, appends keys that do not
exist yet, and never reorders anything.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

#: Keys that carry a secret and must never be echoed back verbatim.
SECRET_KEYS: frozenset[str] = frozenset({"MODEL_API_KEY"})

#: Model presets offered by the UI ("one click instead of three fields").
PRESETS: dict[str, dict[str, str]] = {
    "deepseek-flash": {
        "label": "DeepSeek V4.1-Flash",
        "MODEL_API_BASE_URL": "https://api.deepseek.com",
        "MODEL_NAME": "deepseek-flash",
        "MODEL_THINKING": "auto",
        "MODEL_REASONING_EFFORT": "low",
    },
    "deepseek-pro": {
        "label": "DeepSeek V4-Pro",
        "MODEL_API_BASE_URL": "https://api.deepseek.com",
        "MODEL_NAME": "deepseek-v4-pro",
        "MODEL_THINKING": "auto",
        "MODEL_REASONING_EFFORT": "low",
    },
    "openai": {
        "label": "OpenAI GPT-4o mini",
        "MODEL_API_BASE_URL": "https://api.openai.com/v1",
        "MODEL_NAME": "gpt-4o-mini",
        "MODEL_THINKING": "disabled",
        "MODEL_REASONING_EFFORT": "",
    },
    "moonshot": {
        "label": "月之暗面 Kimi",
        "MODEL_API_BASE_URL": "https://api.moonshot.cn/v1",
        "MODEL_NAME": "moonshot-v1-32k",
        "MODEL_THINKING": "disabled",
        "MODEL_REASONING_EFFORT": "",
    },
    "dashscope": {
        "label": "阿里云百炼 Qwen",
        "MODEL_API_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "MODEL_NAME": "qwen-plus",
        "MODEL_THINKING": "disabled",
        "MODEL_REASONING_EFFORT": "",
    },
}

#: Every key the configuration form is allowed to touch.
ALLOWED_KEYS: tuple[str, ...] = (
    "MODEL_API_BASE_URL",
    "MODEL_API_KEY",
    "MODEL_NAME",
    "MODEL_ANALYST_NAME",
    "MODEL_CRITIC_NAME",
    "MODEL_PROVIDER",
    "MODEL_THINKING",
    "MODEL_REASONING_EFFORT",
    "MODEL_API_TIMEOUT_SECONDS",
    "SPLICEGAIP_LLM_LANG",
    "SPLICEGAIP_LLM_FEATURES",
    "SPLICEGAIP_LLM_ENABLED",
    "SPLICEGAIP_LLM_TIMEOUT",
    "SPLICEGAIP_LLM_MAX_CALLS",
    "SPLICEGAIP_LLM_MAX_GENES",
    "SPLICEGAIP_ENABLE_PUBMED",
)


#: File names that are recognised as "the local configuration file".
#: ``配置大模型.env`` shipped next to the desktop exe as a friendlier name;
#: users filled it in, so it must be honoured exactly like ``.env``.
CONFIG_FILE_NAMES: tuple[str, ...] = (".env", "配置大模型.env")


def project_root() -> Path:
    """Directory that holds the sources (or the frozen bundle's contents)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def search_directories() -> list[Path]:
    """Directories a configuration file is looked for in, in priority order.

    The runtime directory (frozen exe dir, then the current working
    directory) always wins over the *source tree* ``project_root``. This
    matters because a deployed exe must never pick up a developer's
    placeholder ``.env`` (which may carry a fake key) sitting in the source
    checkout. When frozen we therefore skip ``project_root`` entirely.
    """
    directories: list[Path] = []
    if getattr(sys, "frozen", False):
        directories.append(Path(sys.executable).resolve().parent)
    directories.append(Path.cwd())
    if not getattr(sys, "frozen", False):
        directories.append(project_root())
    ordered: list[Path] = []
    seen: set[Path] = set()
    for directory in directories:
        try:
            resolved = directory.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def candidate_env_paths() -> list[Path]:
    """Every file path that may hold configuration, highest priority first."""
    return [directory / name for directory in search_directories() for name in CONFIG_FILE_NAMES]


def existing_env_paths() -> list[Path]:
    """All configuration files that actually exist (priority order)."""
    return [path for path in candidate_env_paths() if path.is_file()]


def existing_env_path() -> Path | None:
    """The file new writes go to (the first candidate that exists)."""
    found = existing_env_paths()
    return found[0] if found else None


def default_env_path() -> Path:
    """The file new writes go to (the frozen bundle wins over the source tree)."""
    return candidate_env_paths()[0]


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        # utf-8-sig tolerates the BOM Notepad writes; without it the first
        # key would silently become "\ufeffMODEL_API_BASE_URL".
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return values
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def collect_env_values() -> tuple[dict[str, str], list[Path]]:
    """Merge every configuration file that exists.

    Files are read highest priority first and the **first non-empty value**
    for a key wins, so a credential found in a lower-priority file
    (``配置大模型.env``) is still honoured when the higher-priority one
    (``.env``) leaves it blank. Returns the merged values and the files read.
    """
    merged: dict[str, str] = {}
    sources: list[Path] = []
    for path in candidate_env_paths():
        if not path.is_file():
            continue
        values = read_env_file(path)
        sources.append(path)
        for key, value in values.items():
            if value and not merged.get(key):
                merged[key] = value
    return merged, sources


def load_env_values() -> list[Path]:
    """Apply :func:`collect_env_values` to ``os.environ`` without overriding.

    Existing environment variables keep precedence (a launcher or shell still
    wins); returns the list of files that were read so the caller can report
    them to the user.
    """
    merged, sources = collect_env_values()
    for key, value in merged.items():
        os.environ.setdefault(key, value)
    return sources


def current_env_values() -> dict[str, str]:
    """Effective configuration as the running process sees it."""
    values: dict[str, str] = {}
    for key in ALLOWED_KEYS:
        values[key] = str(os.getenv(key, "") or "")
    return values


def write_env_values(updates: dict[str, str]) -> tuple[Path, list[str]]:
    """Merge ``updates`` into the local ``.env`` file.

    Existing keys are rewritten in place (comments kept), new keys are
    appended. Empty values are written as empty lines so a user can clear a
    key again. Secrets are also pushed into ``os.environ`` so the change
    takes effect without a restart.

    :returns: the file written and the list of keys that changed.
    """
    target = existing_env_path() or default_env_path()
    clean: dict[str, str] = {}
    for key, value in updates.items():
        upper = str(key).strip().upper()
        if upper not in ALLOWED_KEYS:
            continue
        clean[upper] = str(value).strip()

    lines: list[str] = []
    if target.is_file():
        try:
            lines = target.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            lines = []
    remaining = dict(clean)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, _value = stripped.partition("=")
        key = key.strip()
        if key in remaining:
            lines[index] = f"{key}={remaining.pop(key)}"
    if remaining:
        if lines and lines[-1].strip():
            lines.append("")
        for key, value in remaining.items():
            lines.append(f"{key}={value}")
    lines.append("")

    written = [_write_one(target, lines)]
    # Keep every recognised configuration file that already exists in sync:
    # two files with different keys are exactly how a filled-in credential
    # ends up "not working" depending on which one the user opened.
    for path in existing_env_paths():
        if path.resolve() == target.resolve():
            continue
        written.append(_write_one(path, list(lines)))

    for key, value in clean.items():
        os.environ[key] = value
    return target, sorted(clean)


def _write_one(target: Path, lines: list[str]) -> Path:
    """Write one configuration file, falling back to no-op on read-only disks."""
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        pass
    return target


def mask(values: dict[str, str]) -> dict[str, str]:
    """Return display-safe values (secrets replaced by a masked preview)."""
    masked = dict(values)
    for key in SECRET_KEYS:
        value = str(masked.get(key, "") or "")
        if not value:
            masked[key] = ""
        elif len(value) <= 8:
            masked[key] = "*" * len(value)
        else:
            masked[key] = f"{value[:4]}****{value[-4:]}"
    return masked


def env_config_payload() -> dict[str, Any]:
    """Everything the UI needs to render the model configuration form."""
    main = existing_env_path()
    _merged, sources = collect_env_values()
    values = mask(current_env_values())
    return {
        "env_path": str(main) if main else str(default_env_path()),
        "env_exists": main is not None,
        "sources": [str(path) for path in sources],
        "file_names": list(CONFIG_FILE_NAMES),
        "values": values,
        "presets": [
            {"id": key, "label": preset["label"], "values": {k: v for k, v in preset.items() if k != "label"}}
            for key, preset in PRESETS.items()
        ],
    }
