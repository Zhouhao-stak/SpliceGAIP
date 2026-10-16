"""Base class for all SpliceGAIP skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    """Result from executing a skill."""

    skill_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseSkill(ABC):
    """Abstract base class for all skills.

    Each skill must implement:
    - name: Human-readable skill name
    - description: What the skill does
    - execute: Main execution logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill identifier (ASCII only for EXE compatibility)."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this skill does."""

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema describing required/optional inputs."""
        return {}

    @abstractmethod
    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute the skill with given parameters.

        Args:
            **kwargs: Parameters matching the input schema

        Returns:
            SkillResult with success/failure and data
        """

    def validate_input(self, **kwargs: Any) -> tuple[bool, str | None]:
        """Validate input parameters against the schema.

        Returns:
            (is_valid, error_message)
        """
        schema = self.input_schema
        if not schema:
            return True, None

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for param in required:
            if param not in kwargs or kwargs[param] is None:
                return False, f"Missing required parameter: {param}"

        return True, None
