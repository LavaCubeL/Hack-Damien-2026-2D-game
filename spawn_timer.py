"""Reusable spawn countdown helper.

SpawnTimer keeps random spawn timing out of the main game loop.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class SpawnTimer:
    minimum: int
    maximum: int
    value: int = 0

    def reset(self) -> None:
        self.value = random.randint(self.minimum, self.maximum)

    def tick(self) -> bool:
        self.value -= 1
        return self.value <= 0

