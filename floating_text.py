"""Atmospheric text that drifts through the cave."""

from __future__ import annotations

import random

import pygame

from settings import ACCENT, HAZARD, TEXT, WIDTH


class FloatingText:
    """Short atmospheric messages that drift across the cave."""

    MESSAGES = (
        "KEEP MOVING",
        "THE CAVE IS AWAKE",
        "LOW CEILING",
        "DON'T BLINK",
        "SIGNAL LOST",
        "LASER HEAT RISING",
        "RUN FASTER",
        "WATCH THE FLOOR",
    )

    def __init__(self, font: pygame.font.Font, score: int) -> None:
        self.text = random.choice(self.MESSAGES)
        if score > 1800 and random.random() < 0.4:
            self.text = random.choice(("LASER INBOUND", "REALITY SHIFT", "STAY LOW", "GLITCH EVENT"))

        color = random.choice((TEXT, ACCENT, HAZARD))
        self.image = font.render(self.text, True, color)
        self.image.set_alpha(0)
        self.rect = self.image.get_rect(midleft=(WIDTH + 30, random.randint(125, 310)))
        self.life = 190
        self.alpha = 0

    def update(self, speed: float) -> None:
        self.rect.x -= round(speed * 0.85)
        self.life -= 1
        self.alpha = min(210, self.alpha + 8) if self.life > 55 else max(0, self.alpha - 6)
        self.image.set_alpha(self.alpha)

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self.image, self.rect)

    @property
    def alive(self) -> bool:
        return self.life > 0 and self.rect.right > -30
