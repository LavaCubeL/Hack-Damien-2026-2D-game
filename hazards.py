"""Projectile and explosive hazard classes.

The main Game class owns when hazards spawn; these classes own timing,
collision checks, and drawing.
"""

from __future__ import annotations

import math
import random

import pygame

from settings import (
    EXPLOSIVE,
    FLOOR_Y,
    HAZARD,
    LASER_CORE,
    ROCK,
    ROCK_DARK,
    TEXT,
    WIDTH,
)


class LaserBeam:
    """Warning line followed by a damaging laser hazard."""

    def __init__(self, y: int) -> None:
        self.y = y
        self.charge_frames = 84
        self.fire_frames = 34
        self.cooldown_frames = 18
        self.age = 0
        self.active = False
        self.done = False
        self.hitbox = pygame.Rect(0, y - 13, WIDTH, 26)

    def update(self) -> None:
        self.age += 1
        self.active = self.charge_frames <= self.age < self.charge_frames + self.fire_frames
        self.done = self.age >= self.charge_frames + self.fire_frames + self.cooldown_frames

    def collides_with(self, rect: pygame.Rect) -> bool:
        return self.active and self.hitbox.colliderect(rect)

    def draw(self, screen: pygame.Surface) -> None:
        if self.age < self.charge_frames:
            alpha = 80 + int(math.sin(self.age * 0.55) * 55)
            warning = pygame.Surface((WIDTH, 34), pygame.SRCALPHA)
            pygame.draw.line(warning, (255, 60, 92, alpha), (0, 17), (WIDTH, 17), 3)
            pygame.draw.line(warning, (255, 240, 190, alpha), (0, 17), (WIDTH, 17), 1)
            screen.blit(warning, (0, self.y - 17))
            return

        if self.active:
            beam = pygame.Surface((WIDTH, 72), pygame.SRCALPHA)
            pulse = 8 + int(math.sin(self.age * 0.8) * 5)
            pygame.draw.rect(beam, (255, 38, 88, 95), (0, 18 - pulse, WIDTH, 36 + pulse * 2))
            pygame.draw.rect(beam, (255, 118, 142, 165), (0, 26 - pulse // 2, WIDTH, 20 + pulse))
            pygame.draw.rect(beam, LASER_CORE, (0, 33, WIDTH, 6))
            screen.blit(beam, (0, self.y - 36), special_flags=pygame.BLEND_RGBA_ADD)


class Explosive(pygame.sprite.Sprite):
    """Boss explosive that gives a warning before detonating."""

    def __init__(self, x: int, speed: float) -> None:
        super().__init__()
        self.speed = speed * 0.45
        self.fuse_frames = random.randint(88, 118)
        self.blast_frames = 28
        self.age = 0
        self.radius = 76
        self.done = False
        self.active = False
        self.image = pygame.Surface((54, 58), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midbottom=(x, FLOOR_Y))
        self._draw_bomb(0)

    def update(self, speed: float) -> None:
        self.age += 1
        self.rect.x -= round(self.speed + speed * 0.18)
        self.active = self.fuse_frames <= self.age < self.fuse_frames + self.blast_frames
        self.done = self.age >= self.fuse_frames + self.blast_frames or self.rect.right < -self.radius

        if self.active:
            self._draw_blast()
        else:
            self._draw_bomb(self.age)

        if self.done:
            self.kill()

    def collides_with(self, rect: pygame.Rect) -> bool:
        if not self.active:
            return False

        dx = rect.centerx - self.rect.centerx
        dy = rect.centery - self.rect.centery
        return math.hypot(dx, dy) < self.radius

    def _draw_bomb(self, age: int) -> None:
        self.image = pygame.Surface((54, 58), pygame.SRCALPHA)
        flash = age % 18 < 8
        body_color = EXPLOSIVE if flash else ROCK_DARK
        pygame.draw.ellipse(self.image, body_color, (8, 16, 38, 34))
        pygame.draw.rect(self.image, ROCK, (23, 9, 8, 13), border_radius=3)
        pygame.draw.line(self.image, HAZARD, (27, 9), (35, 1), 3)
        pygame.draw.circle(self.image, LASER_CORE if flash else HAZARD, (37, 0), 4)
        pygame.draw.circle(self.image, TEXT, (21, 29), 4)

    def _draw_blast(self) -> None:
        size = self.radius * 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        center = self.radius
        pulse = int(math.sin(self.age * 0.8) * 8)
        pygame.draw.circle(self.image, (255, 194, 74, 110), (center, center), self.radius + pulse)
        pygame.draw.circle(self.image, (255, 76, 54, 175), (center, center), self.radius - 18)
        pygame.draw.circle(self.image, (255, 242, 166, 220), (center, center), self.radius - 43)
        self.rect = self.image.get_rect(center=self.rect.center)
