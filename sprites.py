"""Player, terrain, and non-boss cave sprite classes.

These classes own their own drawing and update logic so Game can simply
coordinate sprite groups.
"""

from __future__ import annotations

import random

import pygame

from settings import (
    ACCENT,
    GRAVITY,
    GROUND,
    GROUND_DARK,
    HAZARD,
    HEIGHT,
    JUMP_SPEED,
    PLAYER,
    PLAYER_DARK,
    ROCK,
    ROCK_DARK,
    STONE,
    STONE_DARK,
    TEXT,
    VOID,
)


class Player(pygame.sprite.Sprite):
    """The runner controlled by the player."""

    def __init__(self, x: int, ground_y: int) -> None:
        super().__init__()
        self.ground_y = ground_y
        self.image = self._make_image()
        self.rect = self.image.get_rect(midbottom=(x, ground_y))
        self.mask = pygame.mask.from_surface(self.image)
        self.velocity_y = 0.0
        self.jumps_used = 0
        self.max_jumps = 2
        self.alive = True

    def _make_image(self) -> pygame.Surface:
        surface = pygame.Surface((54, 62), pygame.SRCALPHA)
        x, y = 27, 31
        pygame.draw.circle(surface,PLAYER_DARK,(x,y),25)
        '''
        pygame.draw.rect(surface, PLAYER, (10, 14, 32, 35), border_radius=4)
        pygame.draw.rect(surface, PLAYER, (25, 0, 24, 22), border_radius=4)
        pygame.draw.rect(surface, PLAYER_DARK, (13, 48, 8, 14))
        pygame.draw.rect(surface, PLAYER_DARK, (32, 48, 8, 14))
        pygame.draw.rect(surface, PLAYER_DARK, (0, 26, 16, 9), border_radius=3)
        pygame.draw.circle(surface, STONE_DARK, (41, 8), 3)
        pygame.draw.rect(surface, TEXT, (43, 18, 8, 4), border_radius=2)
        '''
        return surface

    @property
    def on_ground(self) -> bool:
        return self.rect.bottom >= self.ground_y - 1

    def jump(self) -> None:
        if self.alive and self.jumps_used < self.max_jumps:
            self.velocity_y = JUMP_SPEED
            self.jumps_used += 1

    def fast_fall(self) -> None:
        if not self.on_ground and self.alive:
            self.velocity_y += 1.25

    def update(self) -> None:
        self.velocity_y += GRAVITY
        self.rect.y += round(self.velocity_y)

        if self.rect.bottom >= self.ground_y:
            self.rect.bottom = self.ground_y
            self.velocity_y = 0
            self.jumps_used = 0


class GroundChunk(pygame.sprite.Sprite):
    """Scrolling cave floor segment."""

    def __init__(self, x: int, y: int, width: int) -> None:
        super().__init__()
        self.image = pygame.Surface((width, HEIGHT - y), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x, y))
        self._draw_chunk()

    def _draw_chunk(self) -> None:
        self.image.fill(GROUND)
        pygame.draw.rect(self.image, GROUND_DARK, (0, 0, self.rect.width, 12))

        for x in range(0, self.rect.width, 34):
            height = random.randint(8, 22)
            color = STONE_DARK if x % 68 == 0 else STONE
            pygame.draw.polygon(
                self.image,
                color,
                [(x, 12), (x + 18, 12), (x + 9, 12 + height)],
            )

    def update(self, speed: float) -> None:
        self.rect.x -= round(speed)


class CeilingChunk(pygame.sprite.Sprite):
    """Scrolling cave ceiling segment with stalactites."""

    def __init__(self, x: int, width: int) -> None:
        super().__init__()
        self.image = pygame.Surface((width, 130), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x, 0))
        self._draw_chunk()

    def _draw_chunk(self) -> None:
        pygame.draw.rect(self.image, STONE_DARK, (0, 0, self.rect.width, 56))
        pygame.draw.rect(self.image, STONE, (0, 50, self.rect.width, 10))

        for x in range(10, self.rect.width, 46):
            width = random.randint(16, 32)
            height = random.randint(28, 72)
            pygame.draw.polygon(
                self.image,
                STONE,
                [(x, 54), (x + width, 54), (x + width // 2, 54 + height)],
            )

    def update(self, speed: float) -> None:
        self.rect.x -= round(speed)


class Obstacle(pygame.sprite.Sprite):
    """Ground spike or boulder obstacle."""

    def __init__(self, x: int, ground_y: int, speed: float) -> None:
        super().__init__()
        self.speed = speed
        self.kind = random.choice(("stalagmite", "boulder"))
        self.image = self._make_image()
        self.rect = self.image.get_rect(midbottom=(x, ground_y))
        self.mask = pygame.mask.from_surface(self.image)

    def _make_image(self) -> pygame.Surface:
        if self.kind == "boulder":
            surface = pygame.Surface((48, 42), pygame.SRCALPHA)
            pygame.draw.ellipse(surface, ROCK, (2, 5, 44, 34))
            pygame.draw.ellipse(surface, ROCK_DARK, (7, 14, 14, 10))
            pygame.draw.ellipse(surface, STONE_DARK, (26, 11, 12, 8))
            return surface

        surface = pygame.Surface((46, 74), pygame.SRCALPHA)
        pygame.draw.polygon(surface, ROCK, [(2, 74), (22, 0), (44, 74)])
        pygame.draw.polygon(surface, ROCK_DARK, [(22, 0), (44, 74), (29, 74)])
        return surface

    def update(self, speed: float) -> None:
        self.speed = speed
        self.rect.x -= round(self.speed)
        if self.rect.right < -20:
            self.kill()


class FallingRock(pygame.sprite.Sprite):
    """Rock that drops from the ceiling while the cave scrolls."""

    def __init__(self, x: int, speed: float) -> None:
        super().__init__()
        self.speed_x = speed * 0.65
        self.speed_y = random.uniform(3.6, 6.2)
        self.image = pygame.Surface((34, 34), pygame.SRCALPHA)
        pygame.draw.polygon(
            self.image,
            ROCK,
            [(8, 2), (28, 5), (33, 21), (20, 33), (4, 27), (1, 11)],
        )
        pygame.draw.line(self.image, ROCK_DARK, (9, 7), (27, 22), 3)
        pygame.draw.circle(self.image, HAZARD, (25, 10), 3)
        self.rect = self.image.get_rect(midtop=(x, random.randint(70, 130)))
        self.mask = pygame.mask.from_surface(self.image)

    def update(self) -> None:
        self.rect.x -= round(self.speed_x)
        self.rect.y += round(self.speed_y)
        self.speed_y += 0.08

        if self.rect.top > HEIGHT or self.rect.right < -20:
            self.kill()


class CaveRelic(pygame.sprite.Sprite):
    """Harmless random cave visual that appears as the run gets stranger."""

    def __init__(self, x: int, y: int, speed: float) -> None:
        super().__init__()
        self.speed = speed * random.uniform(0.45, 0.85)
        self.life = random.randint(130, 220)
        self.image = self._make_image()
        self.base_image = self.image.copy()
        self.rect = self.image.get_rect(center=(x, y))

    def _make_image(self) -> pygame.Surface:
        surface = pygame.Surface((72, 72), pygame.SRCALPHA)
        kind = random.choice(("rune", "eyes", "crystal"))

        if kind == "eyes":
            pygame.draw.circle(surface, VOID, (24, 34), 13)
            pygame.draw.circle(surface, VOID, (50, 34), 13)
            pygame.draw.circle(surface, ACCENT, (24, 34), 5)
            pygame.draw.circle(surface, ACCENT, (50, 34), 5)
        elif kind == "crystal":
            pygame.draw.polygon(surface, ACCENT, [(36, 4), (58, 32), (42, 68), (18, 60), (12, 28)])
            pygame.draw.polygon(surface, TEXT, [(36, 4), (47, 31), (36, 55), (22, 31)])
            surface.set_alpha(190)
        else:
            pygame.draw.circle(surface, VOID, (36, 36), 28, 4)
            pygame.draw.line(surface, ACCENT, (22, 36), (50, 36), 4)
            pygame.draw.line(surface, ACCENT, (36, 22), (36, 50), 4)
            pygame.draw.circle(surface, HAZARD, (36, 36), 5)

        return surface

    def update(self, speed: float) -> None:
        self.rect.x -= round(self.speed + speed * 0.15)
        self.life -= 1
        alpha = max(0, min(210, self.life * 3))
        self.image = self.base_image.copy()
        self.image.set_alpha(alpha)

        if self.life <= 0 or self.rect.right < -40:
            self.kill()
