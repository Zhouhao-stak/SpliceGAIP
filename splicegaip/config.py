"""Configuration loading for SpliceGAIP.

Resolution order (later wins):
  1. ``config/config.yaml`` shipped with the project
  2. environment variables prefixed ``SPLICEGAIP_``
  3. ``.env``-style ``KEY=VALUE`` lines in ``SPLICEGAIP_ENV_FILE`` (optional)

LLM credentials are NEVER stored in config files. They are read from
environment variables only (``MODEL_API_BASE_URL`` / ``MODEL_API_KEY`` /
``MODEL_NAME``), matching the convention used by SplicingNexus v2.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_AGENT_CONFIG_PATH = PROJECT_ROOT / "config" / "agent_config.yaml"


class ConfigError(RuntimeError):
    """Raised when the configuration is missing or invalid."""


@dataclass(frozen=True)
class LLMSettings:
    """OpenAI-compatible model endpoint settings.

    All values come from the environment; ``configured`` is False when no
    API key is present, in which case the platform runs the deterministic
    offline policy instead of an LLM.
    """

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    analyst_model: str = ""
    critic_model: str = ""
    timeout_seconds: float = 600.0
    temperature: float = 0.2
    # -- non-secret knobs (YAML "llm:" block, overridable by env) ----------
    enabled: bool = True
    #: Which enrichment features may call the model ("all" or a subset).
    features: tuple[str, ...] = ()
    #: Per-call timeout for the enrichment layer (the agent client keeps
    #: ``timeout_seconds``, which is much longer on purpose).
    insight_timeout_seconds: float = 120.0
    #: Safety budget: how many enrichment calls one analysis run may make.
    max_calls_per_run: int = 16
    #: How many top genes receive per-gene AI annotation / evidence summary.
    max_genes: int = 8
    #: "auto" (detect from the query), "zh", "en".
    language: str = "auto"
    # -- provider-specific knobs ------------------------------------------
    #: Endpoint family: "auto" (guess from base_url/model), or one of
    #: deepseek / openai / moonshot / dashscope / generic. Non-secret; it
    #: only decides which vendor-specific request fields are safe to send.
    provider: str = "auto"
    #: Reasoning mode for vendors that expose one (currently DeepSeek).
    #: "auto" keeps tool-calling safe (see :mod:`splicegaip.llm.client`),
    #: "enabled"/"disabled" force it either way.
    thinking: str = "auto"
    #: Reasoning effort when thinking is enabled ("", minimal, low, medium,
    #: high, xhigh, max). Empty means "use the vendor default".
    reasoning_effort: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url)

    @property
    def usable(self) -> bool:
        """Configured *and* switched on, with a model name to call."""
        return self.configured and self.enabled and bool(self.model)


@dataclass(frozen=True)
class SkillSettings:
    """External (network-backed) knowledge skills used by the agent.

    Everything here is optional: when disabled or unreachable, the agent
    simply continues with the local analysis and records the gap.
    """

    #: Master switch; ``SPLICEGAIP_ENABLE_SKILLS`` overrides it at runtime.
    enabled: bool = True
    #: Hard cap on network-backed calls per run.
    max_calls: int = 4
    #: Per-call wall-clock budget (seconds).
    timeout: float = 10.0


@dataclass(frozen=True)
class AgentSettings:
    """Autonomous-agent behaviour (see :mod:`splicegaip.agent`).

    ``mode`` selects the execution engine:

    * ``agentic``  — the autonomous observe/decide/act/verify loop;
    * ``scripted`` — the legacy fixed multi-agent script (bit-compatible).
    """

    mode: str = "agentic"
    max_steps: int = 20
    max_seconds: float = 900.0
    max_errors: int = 3
    #: Allow the agent to choose FDR / |dPSI| from the data instead of the
    #: configured defaults when the defaults yield nothing usable.
    adaptive_thresholds: bool = True
    #: Significant-event count the adaptive policy aims for.
    target_significant: int = 100
    #: Verify results and remediate problems (self-correction).
    reflection: bool = True
    #: Ask the model for an extra insight step when the mandatory work is done.
    llm_advisory: bool = True
    #: Remember decisions across runs (episodic memory).
    episodic: bool = True
    #: "auto" = fully autonomous; "assisted" asks before risky decisions
    #: (network calls, threshold relaxation, accepting a blocker).
    autonomy: str = "auto"
    #: External knowledge skills (Phase 2).
    skills: SkillSettings = field(default_factory=SkillSettings)
    #: Run the pre-registered statistical hypothesis tests before interpreting.
    hypothesis_testing: bool = True

    @property
    def agentic(self) -> bool:
        return str(self.mode).strip().lower() in {"agentic", "agent", "auto"}

    @property
    def assisted(self) -> bool:
        return str(self.autonomy).strip().lower() == "assisted"


@dataclass(frozen=True)
class AnalysisSettings:
    fdr_threshold: float = 0.05
    delta_psi_threshold: float = 0.1
    min_support_reads: int = 10
    min_valid_samples: int = 2
    top_candidates: int = 20
    enrichment_alpha: float = 0.05


def default_runtime_root() -> Path:
    """Platform-safe default for the runtime root.

    Linux/macOS keep the historical ``/var/tmp/splicegaip`` (local disk, so
    SQLite byte-range locking works even when the home directory is on NFS).
    Windows has no ``/var/tmp`` — a POSIX-looking absolute path there silently
    resolves to ``C:\\var\\tmp`` relative to the current drive, which is both
    surprising and sometimes not creatable. Use the real temp dir instead.
    """
    if os.name == "nt":
        import tempfile

        return Path(tempfile.gettempdir()) / "splicegaip"
    return Path("/var/tmp/splicegaip")


@dataclass(frozen=True)
class PathSettings:
    #: Runtime root. Defaults to local disk (``/var/tmp`` on POSIX, the system
    #: temp dir on Windows): SQLite state cannot live on NFS mounts.
    runtime_root: Path = field(default_factory=default_runtime_root)
    memory_db: Path = field(
        default_factory=lambda: default_runtime_root() / "splicegaip.sqlite3"
    )
    literature_db: Path = field(
        default_factory=lambda: default_runtime_root() / "literature.sqlite3"
    )


@dataclass(frozen=True)
class Settings:
    project_name: str
    version: str
    paths: PathSettings
    llm: LLMSettings
    analysis: AnalysisSettings
    report_formats: tuple[str, ...] = ("html", "pdf")
    agent: AgentSettings = field(default_factory=AgentSettings)
    raw: dict[str, Any] = field(default_factory=dict)

    def resolve(self, relative: str | Path) -> Path:
        path = Path(relative)
        return path if path.is_absolute() else (PROJECT_ROOT / path)


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Map ``SPLICEGAIP_*`` environment variables onto the config tree."""
    overrides = {
        "paths.runtime_root": os.getenv("SPLICEGAIP_RUNTIME_ROOT"),
        "paths.memory_db": os.getenv("SPLICEGAIP_MEMORY_DB"),
        "paths.literature_db": os.getenv("SPLICEGAIP_LITERATURE_DB"),
        "analysis.fdr_threshold": os.getenv("SPLICEGAIP_FDR_THRESHOLD"),
        "analysis.delta_psi_threshold": os.getenv("SPLICEGAIP_DELTA_PSI_THRESHOLD"),
        "analysis.top_candidates": os.getenv("SPLICEGAIP_TOP_CANDIDATES"),
    }
    for dotted, value in overrides.items():
        if value is None:
            continue
        section, _, key = dotted.partition(".")
        # ``paths:`` with every key commented out parses as None, so
        # setdefault() would hand back None instead of a fresh dict.
        section_map = data.get(section)
        if not isinstance(section_map, dict):
            section_map = {}
            data[section] = section_map
        section_map[key] = value
    return data


def _env_str(name: str, fallback: str = "") -> str:
    value = os.getenv(name)
    return value if value is not None else fallback


def _llm_settings(data: dict[str, Any] | None = None) -> LLMSettings:
    """Build LLM settings: secrets from the environment only.

    Non-secret knobs may also come from the ``llm:`` block in
    ``config/config.yaml``; environment variables always win.
    """
    block = data or {}
    if not isinstance(block, dict):
        block = {}
    raw_features = block.get("features", ())
    if isinstance(raw_features, str):
        raw_features = tuple(item.strip() for item in raw_features.split(",") if item.strip())
    elif isinstance(raw_features, (list, tuple)):
        raw_features = tuple(str(item).strip() for item in raw_features if str(item).strip())
    else:
        raw_features = ()
    env_features = _env_str("SPLICEGAIP_LLM_FEATURES")
    if env_features:
        raw_features = tuple(item.strip() for item in env_features.split(",") if item.strip())
    enabled_raw = str(block.get("enabled", True))
    enabled = os.getenv("SPLICEGAIP_LLM_ENABLED", enabled_raw).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return LLMSettings(
        base_url=os.getenv("MODEL_API_BASE_URL", "").rstrip("/"),
        api_key=os.getenv("MODEL_API_KEY", ""),
        model=os.getenv("MODEL_NAME", ""),
        analyst_model=os.getenv("MODEL_ANALYST_NAME", "") or os.getenv("MODEL_NAME", ""),
        critic_model=os.getenv("MODEL_CRITIC_NAME", "") or os.getenv("MODEL_NAME", ""),
        timeout_seconds=float(os.getenv("MODEL_API_TIMEOUT_SECONDS", "600")),
        temperature=float(os.getenv("SPLICEGAIP_TEMPERATURE", "0.2")),
        enabled=enabled,
        features=raw_features,
        insight_timeout_seconds=float(
            os.getenv("SPLICEGAIP_LLM_TIMEOUT", str(block.get("insight_timeout_seconds", 120)))
        ),
        max_calls_per_run=int(
            os.getenv("SPLICEGAIP_LLM_MAX_CALLS", str(block.get("max_calls_per_run", 16)))
        ),
        max_genes=int(os.getenv("SPLICEGAIP_LLM_MAX_GENES", str(block.get("max_genes", 8)))),
        language=str(os.getenv("SPLICEGAIP_LLM_LANG", str(block.get("language", "auto")))),
        provider=str(os.getenv("MODEL_PROVIDER", str(block.get("provider", "auto"))) or "auto"),
        thinking=str(os.getenv("MODEL_THINKING", str(block.get("thinking", "auto"))) or "auto"),
        reasoning_effort=str(
            os.getenv("MODEL_REASONING_EFFORT", str(block.get("reasoning_effort", "")) ) or ""
        ).strip(),
    )


def _agent_settings(data: dict[str, Any] | None = None) -> AgentSettings:
    """Build autonomous-agent settings (YAML ``agent:`` block + env)."""
    block = data or {}
    if not isinstance(block, dict):
        block = {}

    def _bool(name: str, key: str, default: bool) -> bool:
        raw = os.getenv(name, str(block.get(key, default)))
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def _int(name: str, key: str, default: int) -> int:
        raw = os.getenv(name, str(block.get(key, default)))
        try:
            return int(str(raw).strip())
        except (TypeError, ValueError):
            return default

    def _float(name: str, key: str, default: float) -> float:
        raw = os.getenv(name, str(block.get(key, default)))
        try:
            return float(str(raw).strip())
        except (TypeError, ValueError):
            return default

    skills_block = block.get("skills") or {}
    if not isinstance(skills_block, dict):
        skills_block = {}

    def _skill_bool(env: str, key: str, default: bool) -> bool:
        raw = os.getenv(env, str(skills_block.get(key, default)))
        if raw is None:
            return default
        value = str(raw).strip().lower()
        if value in {"1", "true", "yes", "on", "enabled"}:
            return True
        if value in {"0", "false", "no", "off", "disabled", "none"}:
            return False
        return default

    def _skill_int(env: str, key: str, default: int) -> int:
        raw = os.getenv(env, skills_block.get(key, default))
        try:
            return int(str(raw).strip())
        except (TypeError, ValueError):
            return default

    def _skill_float(env: str, key: str, default: float) -> float:
        raw = os.getenv(env, skills_block.get(key, default))
        try:
            return float(str(raw).strip())
        except (TypeError, ValueError):
            return default

    skills = SkillSettings(
        enabled=_skill_bool("SPLICEGAIP_ENABLE_SKILLS", "enabled", True),
        max_calls=max(_skill_int("SPLICEGAIP_SKILLS_MAX_CALLS", "max_calls", 4), 0),
        timeout=max(_skill_float("SPLICEGAIP_SKILLS_TIMEOUT", "timeout", 10.0), 1.0),
    )

    return AgentSettings(
        mode=str(os.getenv("SPLICEGAIP_AGENT_MODE", block.get("mode", "agentic")) or "agentic"),
        max_steps=max(_int("SPLICEGAIP_AGENT_MAX_STEPS", "max_steps", 20), 1),
        max_seconds=max(_float("SPLICEGAIP_AGENT_MAX_SECONDS", "max_seconds", 900.0), 1.0),
        max_errors=max(_int("SPLICEGAIP_AGENT_MAX_ERRORS", "max_errors", 3), 1),
        adaptive_thresholds=_bool("SPLICEGAIP_AGENT_ADAPTIVE", "adaptive_thresholds", True),
        target_significant=max(_int("SPLICEGAIP_AGENT_TARGET", "target_significant", 100), 1),
        reflection=_bool("SPLICEGAIP_AGENT_REFLECTION", "reflection", True),
        llm_advisory=_bool("SPLICEGAIP_AGENT_LLM_ADVISORY", "llm_advisory", True),
        episodic=_bool("SPLICEGAIP_AGENT_EPISODIC", "episodic", True),
        autonomy=str(os.getenv("SPLICEGAIP_AUTONOMY", block.get("autonomy", "auto")) or "auto"),
        skills=skills,
        hypothesis_testing=_bool("SPLICEGAIP_HYPOTHESIS_TESTING", "hypothesis_testing", True),
    )


def pubmed_enabled() -> bool:
    """Whether live PubMed retrieval is enabled (default: true).

    Set ``SPLICEGAIP_ENABLE_PUBMED=false`` to skip network retrieval and
    rely on the bundled knowledge base only.
    """
    return os.getenv("SPLICEGAIP_ENABLE_PUBMED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def load_prepared_settings(config_path: str | Path | None = None) -> tuple[Settings, list[str]]:
    """Load settings and relocate SQLite state off unusable filesystems."""
    settings = load_settings(config_path)
    return prepare_storage(settings)


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings from YAML plus environment overrides."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    env_file = os.getenv("SPLICEGAIP_ENV_FILE")
    if env_file:
        for key, value in _load_env_file(Path(env_file)).items():
            os.environ.setdefault(key, value)

    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data = _apply_env_overrides(data)
    # ``paths:`` with every key commented out parses as None, not {}.
    project = data.get("project") or {}
    paths_data = data.get("paths") or {}
    analysis_data = data.get("analysis") or {}
    report_data = data.get("report") or {}
    llm_data = data.get("llm") or {}
    if not isinstance(llm_data, dict):
        llm_data = {}
    agent_data = data.get("agent") or {}
    if not isinstance(agent_data, dict):
        agent_data = {}

    # SQLite state lives *under* the runtime root by default, so that a single
    # SPLICEGAIP_RUNTIME_ROOT relocation moves everything together. Explicit
    # YAML values are honoured, but an empty/absent value falls back to the
    # platform default (this is what keeps the Windows desktop build from
    # writing to a non-existent C:\var\tmp).
    runtime_root = Path(paths_data.get("runtime_root") or default_runtime_root())
    memory_db_raw = paths_data.get("memory_db") or ""
    literature_db_raw = paths_data.get("literature_db") or ""
    legacy = "/var/tmp/splicegaip"
    if os.name == "nt" and memory_db_raw.startswith(legacy):
        # Shipped config still carries the POSIX default: ignore it on Windows
        # so the database follows the runtime root.
        memory_db_raw = ""
    if os.name == "nt" and literature_db_raw.startswith(legacy):
        literature_db_raw = ""
    paths = PathSettings(
        runtime_root=runtime_root,
        memory_db=Path(memory_db_raw) if memory_db_raw else runtime_root / "splicegaip.sqlite3",
        literature_db=(
            Path(literature_db_raw) if literature_db_raw else runtime_root / "literature.sqlite3"
        ),
    )
    analysis = AnalysisSettings(
        fdr_threshold=float(analysis_data.get("fdr_threshold", 0.05)),
        delta_psi_threshold=float(analysis_data.get("delta_psi_threshold", 0.1)),
        min_support_reads=int(analysis_data.get("min_support_reads", 10)),
        min_valid_samples=int(analysis_data.get("min_valid_samples", 2)),
        top_candidates=int(analysis_data.get("top_candidates", 20)),
        enrichment_alpha=float(analysis_data.get("enrichment_alpha", 0.05)),
    )
    formats = report_data.get("formats", ["html", "pdf"])
    return Settings(
        project_name=str(project.get("name", "SpliceGAIP")),
        version=str(project.get("version", "0.1.0")),
        paths=paths,
        llm=_llm_settings(llm_data),
        analysis=analysis,
        report_formats=tuple(str(item) for item in formats),
        agent=_agent_settings(agent_data),
        raw=data,
    )


def ensure_runtime_dirs(settings: Settings) -> None:
    """Create runtime directories if they do not exist yet."""
    for directory in (
        settings.paths.runtime_root,
        settings.paths.memory_db.parent,
        settings.paths.literature_db.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _sqlite_writable(path: Path, timeout: float = 5.0) -> bool:
    """Probe whether a SQLite database can be created at ``path``.

    Some network filesystems (e.g. certain NFS mounts) do not support the
    byte-range locking SQLite requires; opening a database there hangs
    forever. The probe runs in a worker thread with a timeout so a bad
    location fails fast instead of blocking the pipeline.
    """
    import sqlite3
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

    def _probe() -> bool:
        try:
            connection = sqlite3.connect(path, timeout=timeout)
            try:
                connection.execute("CREATE TABLE IF NOT EXISTS _probe (x INTEGER)")
                connection.execute("DROP TABLE _probe")
                connection.commit()
            finally:
                connection.close()
            return True
        except Exception:
            return False

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_probe)
            try:
                return bool(future.result(timeout=timeout + 5))
            except FutureTimeout:
                return False
    except Exception:
        return False


def prepare_storage(settings: Settings) -> tuple[Settings, list[str]]:
    """Validate SQLite locations and relocate them to local disk if needed.

    Returns the (possibly adjusted) settings and a list of warnings.
    """
    warnings: list[str] = []
    fallback_root = Path(os.getenv("SPLICEGAIP_LOCAL_FALLBACK", str(default_runtime_root())))
    changes: dict[str, Path] = {}

    for name in ("memory_db", "literature_db"):
        path = getattr(settings.paths, name)
        if _sqlite_writable(path):
            continue
        fallback = fallback_root / path.name
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        if _sqlite_writable(fallback):
            changes[name] = fallback
            warnings.append(
                f"{name} location {path} is not usable for SQLite (network filesystem?); "
                f"relocated to {fallback}."
            )
        else:
            warnings.append(f"{name} location {path} is not usable for SQLite and no local fallback works.")

    if not changes:
        return settings, warnings

    paths = settings.paths
    updated_paths = PathSettings(
        runtime_root=paths.runtime_root,
        memory_db=changes.get("memory_db", paths.memory_db),
        literature_db=changes.get("literature_db", paths.literature_db),
    )
    raw = dict(settings.raw)
    raw_paths = dict(raw.get("paths") or {})
    raw_paths.update({key: str(value) for key, value in changes.items()})
    raw["paths"] = raw_paths
    return (
        Settings(
            project_name=settings.project_name,
            version=settings.version,
            paths=updated_paths,
            llm=settings.llm,
            analysis=settings.analysis,
        report_formats=settings.report_formats,
        agent=settings.agent,
        raw=raw,
    ),
        warnings,
    )
