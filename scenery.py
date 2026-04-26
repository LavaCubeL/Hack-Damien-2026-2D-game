"""Background scenery and particle effects."""

from __future__ import annotations

import math
import random

import pygame

from settings import ACCENT, HAZARD, HEIGHT, SKY, SNOW, TEXT, WIDTH


class Background:
    """Parallax cave backdrop made from simple drawn shapes."""

    def __init__(self) -> None:
        self.offset = 0
        self.crystals = [
            (random.randint(0, WIDTH), random.randint(150, 370), random.choice((ACCENT, HAZARD, TEXT)))
            for _ in range(34)
        ]

    def update(self, speed: float) -> None:
        self.offset = (self.offset - speed * 0.25) % WIDTH

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(SKY)

        for layer, color in enumerate(((27, 30, 43), (35, 37, 51), (47, 48, 61))):
            y_base = 250 + layer * 42
            points = []
            for i in range(-1, 9):
                x = i * 150 + int(self.offset * (layer + 1) * 0.25)
                y = y_base + ((i * 37 + layer * 53) % 52)
                points.append((x, y))
            points.extend([(WIDTH, HEIGHT), (0, HEIGHT)])
            pygame.draw.polygon(screen, color, points)

        for x, y, color in self.crystals:
            draw_x = (x + int(self.offset)) % WIDTH
            pygame.draw.polygon(screen, color, [(draw_x, y - 7), (draw_x + 5, y), (draw_x, y + 7), (draw_x - 5, y)])


class SnowField:
    """Layered drifting snow/ash particles used by the shader pass."""

    def __init__(self, size: tuple[int, int], count: int = 95) -> None:
        self.width, self.height = size
        self.particles = [self._new_particle(random.randint(0, self.width), random.randint(0, self.height)) for _ in range(count)]

    def _new_particle(self, x: int | None = None, y: int | None = None) -> dict[str, float]:
        return {
            "x": float(random.randint(0, self.width) if x is None else x),
            "y": float(random.randint(-self.height, 0) if y is None else y),
            "size": random.uniform(1.2, 3.8),
            "fall": random.uniform(0.45, 1.8),
            "drift": random.uniform(-0.45, 0.65),
            "phase": random.uniform(0, math.tau),
            "alpha": random.randint(70, 170),
        }

    def update(self, speed: float) -> None:
        for particle in self.particles:
            particle["phase"] += 0.025
            particle["x"] += particle["drift"] - speed * 0.06 + math.sin(particle["phase"]) * 0.22
            particle["y"] += particle["fall"] + min(1.2, speed * 0.035)

            if particle["y"] > self.height + 12 or particle["x"] < -20:
                particle.update(self._new_particle(self.width + random.randint(0, 80), random.randint(-80, -8)))
            elif particle["x"] > self.width + 24:
                particle["x"] = -12

    def draw(self, target: pygame.Surface, intensity: float) -> None:
        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        alpha_scale = min(1.25, 0.55 + intensity * 0.06)

        for particle in self.particles:
            alpha = min(215, int(particle["alpha"] * alpha_scale))
            radius = max(1, int(particle["size"]))
            x = int(particle["x"])
            y = int(particle["y"])
            pygame.draw.circle(layer, (*SNOW, alpha), (x, y), radius)
            if radius > 2:
                pygame.draw.circle(layer, (255, 255, 255, alpha // 3), (x - 1, y - 1), 1)

        target.blit(layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
