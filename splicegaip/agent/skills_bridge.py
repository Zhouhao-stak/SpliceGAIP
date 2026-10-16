"""Bridge between the agent loop and the asynchronous skills.

The four skills in :mod:`splicegaip.skills` are ``async`` and network-bound;
the agent loop is synchronous and must stay running even when the network is
down or a remote API is slow. This module provides the bridge with all the
guards that implies:

* **sync wrapping** — every coroutine runs on its own event loop in a worker
  thread, so it works from a plain script, from FastAPI and from Streamlit;
* **hard timeout** — a slow endpoint can never stall the analysis;
* **kill switch** — ``agent.skills.enabled`` / ``SPLICEGAIP_ENABLE_SKILLS``;
* **budget** — at most ``agent.skills.max_calls`` external calls per run;
* **cache** — the same query is never sent twice within a run;
* **failure is data** — a failed call returns ``None`` and the agent records
  the failure as a limitation instead of crashing or inventing results.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable

_TRUTHY = {"1", "true", "yes", "on", "enabled"}
_FALSY = {"0", "false", "no", "off", "disabled", "none"}

_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=3, thread_name_prefix="splicegaip-skill"
)


def _env_bool(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if value in _TRUTHY:
        return True
    if value in _FALSY:
        return False
    return None


def skills_enabled(settings: Any | None = None) -> bool:
    """Whether external (network) skills may be used at all."""
    override = _env_bool("SPLICEGAIP_ENABLE_SKILLS")
    if override is not None:
        return override
    block = getattr(settings, "agent", None)
    skills = getattr(block, "skills", None)
    return bool(getattr(skills, "enabled", False))


def skill_timeout(settings: Any | None = None) -> float:
    block = getattr(settings, "agent", None)
    skills = getattr(block, "skills", None)
    return float(getattr(skills, "timeout", 10.0) or 10.0)


def skill_budget(settings: Any | None = None) -> int:
    block = getattr(settings, "agent", None)
    skills = getattr(block, "skills", None)
    return int(getattr(skills, "max_calls", 4) or 0)


def _cache_key(name: str, kwargs: dict[str, Any]) -> str:
    payload = json.dumps(kwargs, sort_keys=True, default=str, ensure_ascii=False)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{name}:{digest}"


@dataclass
class SkillCall:
    """Record of one external skill invocation."""

    name: str
    args: dict[str, Any]
    status: str  # ok | empty | failed | disabled | timeout | cached
    detail: str = ""


@dataclass
class SkillBridge:
    """Sync, budgeted, cached access to the async skills."""

    settings: Any | None = None
    enabled: bool = True
    timeout: float = 10.0
    budget: int = 4
    calls: list[SkillCall] = field(default_factory=list)
    _cache: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_settings(cls, settings: Any | None) -> "SkillBridge":
        return cls(
            settings=settings,
            enabled=skills_enabled(settings),
            timeout=skill_timeout(settings),
            budget=skill_budget(settings),
        )

    # -- budget -----------------------------------------------------------
    @property
    def used(self) -> int:
        """Budget consumed so far (a cached answer costs nothing)."""
        return sum(1 for call in self.calls if call.status in {"ok", "empty"})

    @property
    def remaining(self) -> int:
        return max(self.budget - self.used, 0)

    def spent(self) -> bool:
        return self.remaining <= 0

    # -- execution --------------------------------------------------------
    def run_skill(self, name: str, factory: Callable[[], Any], **kwargs: Any) -> Any | None:
        """Execute an async skill and return its ``SkillResult`` (or ``None``)."""
        key = _cache_key(name, kwargs)
        if key in self._cache:
            self.calls.append(SkillCall(name, kwargs, "cached", "served from the run cache"))
            return self._cache[key]

        if not self.enabled:
            self.calls.append(SkillCall(name, kwargs, "disabled", "external skills disabled"))
            return None
        if self.spent():
            self.calls.append(SkillCall(name, kwargs, "failed", "external call budget exhausted"))
            return None

        try:
            skill = factory()
        except Exception as error:  # noqa: BLE001 - a broken skill must not kill the run
            self.calls.append(SkillCall(name, kwargs, "failed", f"skill init failed: {error}"))
            return None

        result = self._invoke(skill, kwargs)
        if result is None:
            self.calls.append(SkillCall(name, kwargs, "timeout", f"no answer within {self.timeout}s"))
            return None
        self._cache[key] = result
        ok = bool(getattr(result, "success", False))
        data = getattr(result, "data", None) or {}
        if ok and data:
            status = "ok"
        elif ok:
            status = "empty"
        else:
            status = "failed"
        detail = str(getattr(result, "error", "") or "")[:200]
        self.calls.append(SkillCall(name, kwargs, status, detail))
        return result if ok else None

    def _invoke(self, skill: Any, kwargs: dict[str, Any]) -> Any | None:
        def _task() -> Any:
            return asyncio.run(skill.execute(**kwargs))

        try:
            future = _EXECUTOR.submit(_task)
            return future.result(timeout=max(self.timeout, 1.0))
        except concurrent.futures.TimeoutError:
            return None
        except Exception:  # noqa: BLE001
            return None

    # -- reporting --------------------------------------------------------
    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "budget": self.budget,
            "used": self.used,
            "calls": [
                {
                    "name": call.name,
                    "status": call.status,
                    "detail": call.detail,
                    "args": {key: str(value)[:120] for key, value in call.args.items()},
                }
                for call in self.calls
            ],
        }

    def summary_line(self) -> str:
        if not self.enabled:
            return "external skills disabled"
        counts: dict[str, int] = {}
        for call in self.calls:
            counts[call.status] = counts.get(call.status, 0) + 1
        rendered = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        return f"external skill calls {self.used}/{self.budget} ({rendered or 'none'})"
