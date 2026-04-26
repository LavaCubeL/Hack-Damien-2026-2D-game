"""Heads-up display rendering."""

from __future__ import annotations

import pygame

from settings import ACCENT, HEIGHT, TEXT, WIDTH


class Hud:
    """Heads-up display for score, speed, and game state."""

    def __init__(self) -> None:
        self.font = pygame.font.Font(None, 34)
        self.big_font = pygame.font.Font(None, 74)

    def draw(self, screen: pygame.Surface, score: int, speed: float, game_over: bool) -> None:
        score_text = self.font.render(f"Meters {score:05d}m", True, TEXT)
        speed_text = self.font.render(f"Speed {speed:.1f}", True, ACCENT)
        self._draw_text(screen, score_text, (24, 20))
        self._draw_text(screen, speed_text, (24, 54))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))

            title = self.big_font.render("CAVE CRASH", True, TEXT)
            hint = self.font.render("Press R to restart or Esc to quit", True, ACCENT)
            self._draw_text(screen, title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 25)))
            self._draw_text(screen, hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 35)))

    def _draw_text(self, screen: pygame.Surface, image: pygame.Surface, position: tuple[int, int] | pygame.Rect) -> None:
        rect = image.get_rect(topleft=position) if isinstance(position, tuple) else position
        shadow = image.copy()
        shadow.fill((0, 0, 0, 180), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(shadow, rect.move(3, 3))
        screen.blit(image, rect)
