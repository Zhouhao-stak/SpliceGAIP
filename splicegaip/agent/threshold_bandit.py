"""Multi-armed bandit for adaptive threshold selection.

Tracks which (FDR, |dPSI|) pairs worked best across runs and weights future
choices using an epsilon-greedy strategy with decaying exploration.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ArmStats:
    """Statistics for one (fdr, dpsi) arm."""

    pulls: int = 0
    total_reward: float = 0.0
    last_reward: float = 0.0

    @property
    def mean_reward(self) -> float:
        if self.pulls == 0:
            return 0.0
        return self.total_reward / self.pulls


@dataclass
class ThresholdBandit:
    """Epsilon-greedy bandit for threshold selection."""

    arms: dict[str, ArmStats] = field(default_factory=dict)
    epsilon: float = 0.1  # exploration rate
    decay: float = 0.95   # epsilon decay per run
    min_epsilon: float = 0.02

    def _key(self, fdr: float, dpsi: float) -> str:
        return f"{fdr:.4f}|{dpsi:.4f}"

    def _parse_key(self, key: str) -> tuple[float, float]:
        parts = key.split("|")
        return float(parts[0]), float(parts[1])

    def get_arm(self, fdr: float, dpsi: float) -> ArmStats:
        key = self._key(fdr, dpsi)
        if key not in self.arms:
            self.arms[key] = ArmStats()
        return self.arms[key]

    def choose(
        self,
        candidates: list[tuple[float, float]],
        counts: dict[tuple[float, float], int],
        goal_target: int,
    ) -> tuple[float, float]:
        """Pick the next arm to pull.

        Uses epsilon-greedy: with probability epsilon explore randomly,
        otherwise exploit the best-known arm from candidates.
        """
        import random

        # Decay epsilon
        self.epsilon = max(self.min_epsilon, self.epsilon * self.decay)

        # Explore: pick randomly from candidates
        if random.random() < self.epsilon or not any(
            self._key(fdr, dpsi) in self.arms for fdr, dpsi in candidates
        ):
            # Weight by how close count is to target
            weights = []
            for fdr, dpsi in candidates:
                count = counts.get((fdr, dpsi), 0)
                # Higher weight for closer to target
                distance = abs(count - goal_target) / max(goal_target, 1)
                weight = 1.0 / (1.0 + distance)
                weights.append(weight)

            # Normalize
            total = sum(weights)
            if total > 0:
                weights = [w / total for w in weights]
                idx = random.choices(range(len(candidates)), weights=weights, k=1)[0]
                return candidates[idx]
            else:
                return candidates[0] if candidates else (0.05, 0.1)

        # Exploit: pick best known arm from candidates
        best_arm = None
        best_mean = -float("inf")
        for fdr, dpsi in candidates:
            arm = self.get_arm(fdr, dpsi)
            if arm.mean_reward > best_mean:
                best_mean = arm.mean_reward
                best_arm = (fdr, dpsi)

        return best_arm if best_arm else candidates[0]

    def update(self, fdr: float, dpsi: float, reward: float) -> None:
        """Record the reward for pulling this arm."""
        arm = self.get_arm(fdr, dpsi)
        arm.pulls += 1
        arm.total_reward += reward
        arm.last_reward = reward

    def save(self, path: str | Path) -> None:
        """Persist bandit state to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "epsilon": self.epsilon,
            "decay": self.decay,
            "min_epsilon": self.min_epsilon,
            "arms": {
                key: {
                    "pulls": arm.pulls,
                    "total_reward": arm.total_reward,
                    "last_reward": arm.last_reward,
                }
                for key, arm in self.arms.items()
            },
        }
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: str | Path) -> None:
        """Load bandit state from disk."""
        path = Path(path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.epsilon = data.get("epsilon", self.epsilon)
            self.decay = data.get("decay", self.decay)
            self.min_epsilon = data.get("min_epsilon", self.min_epsilon)
            self.arms = {
                key: ArmStats(**arm_data)
                for key, arm_data in data.get("arms", {}).items()
            }
        except Exception:
            pass  # Silently ignore corrupt files


def compute_reward(count: int, goal_target: int, fdr: float, dpsi: float) -> float:
    """Compute reward for a threshold choice.

    Reward balances:
    - Proximity to target count (primary)
    - Stringency preference (lower FDR/dPSI when counts are similar)
    """
    # Primary: how close to target
    distance = abs(count - goal_target) / max(goal_target, 1)
    count_reward = 1.0 / (1.0 + distance)

    # Secondary: prefer tighter thresholds (but only slightly)
    stringency = 1.0 - (fdr + dpsi) / 2.0  # normalized to [0, 1]

    # Weighted combination
    return 0.8 * count_reward + 0.2 * stringency
