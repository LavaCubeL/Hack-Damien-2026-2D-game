"""Post-processing screen shader.

This file keeps visual filters separate from gameplay. Ambient event pulses
are intentionally muted so the old blue/cyan flash no longer fires every few
seconds.
"""

from __future__ import annotations

import math
import random

import pygame

from scenery import SnowField
from settings import START_SPEED


class ScreenShader:
    """Post-processing effects drawn after the game scene is rendered."""

    def __init__(self, size: tuple[int, int]) -> None:
        self.width, self.height = size
        self.frame = 0
        self.flash_alpha = 0
        self.laser_alpha = 0
        self.pulse_alpha = 0
        self.glitch_frames = 0
        self.mirror_frames = 0
        self.shake_amount = 0
        self.enabled = True
        self.vignette = self._make_vignette()
        self.scanlines = self._make_scanlines()
        self.snow = SnowField(size)

    def _make_vignette(self) -> pygame.Surface:
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        center_x = self.width / 2
        center_y = self.height / 2
        max_distance = math.hypot(center_x, center_y)

        for y in range(self.height):
            for x in range(self.width):
                distance = math.hypot(x - center_x, y - center_y)
                strength = max(0, (distance / max_distance - 0.38) / 0.62)
                alpha = min(185, int(strength * strength * 210))
                if alpha:
                    surface.set_at((x, y), (0, 0, 0, alpha))

        return surface

    def _make_scanlines(self) -> pygame.Surface:
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 4):
            pygame.draw.line(surface, (0, 0, 0, 42), (0, y), (self.width, y))
        return surface

    def trigger_impact(self) -> None:
        # Impacts should shake the camera without adding another screen flash.
        self.flash_alpha = 0
        self.shake_amount = 16

    def trigger_laser(self) -> None:
        self.laser_alpha = 180
        self.glitch_frames = 24
        self.shake_amount = max(self.shake_amount, 20)

    def trigger_event_pulse(self) -> None:
        """Acknowledge ambient events without flashing cyan on the screen."""
        # Random events happen every couple of seconds, so the old cyan pulse was visually noisy.
        self.pulse_alpha = 0
        self.glitch_frames = 0

    def trigger_screen_flip(self) -> None:
        self.mirror_frames = 150
        self.glitch_frames = max(self.glitch_frames, 28)
        self.pulse_alpha = 0
        self.shake_amount = max(self.shake_amount, 13)

    def update(self, speed: float, game_over: bool) -> None:
        self.frame += 1
        self.flash_alpha = max(0, self.flash_alpha - 9)
        self.laser_alpha = max(0, self.laser_alpha - 12)
        self.pulse_alpha = max(0, self.pulse_alpha - 4)
        self.glitch_frames = max(0, self.glitch_frames - 1)
        self.mirror_frames = max(0, self.mirror_frames - 1)
        self.shake_amount = max(0, self.shake_amount - (0.35 if game_over else 1.1))
        self.snow.update(speed)

        if speed > 9.5 and not game_over:
            self.shake_amount = max(self.shake_amount, min(5, (speed - 9.5) * 0.85))

    def apply(self, source: pygame.Surface, target: pygame.Surface, speed: float, game_over: bool) -> None:
        source_view = pygame.transform.flip(source, True, False) if self.mirror_frames and not game_over else source

        if not self.enabled:
            target.blit(source_view, (0, 0))
            return

        shake_x, shake_y = self._shake_offset()
        target.fill((0, 0, 0))

        chromatic_shift = 1 + min(5, int(speed - START_SPEED))
        if game_over:
            chromatic_shift = min(2, chromatic_shift)

        red_pass = source_view.copy()
        red_pass.fill((255, 72, 72, 255), special_flags=pygame.BLEND_RGBA_MULT)
        red_pass.set_alpha(42)

        blue_pass = source_view.copy()
        blue_pass.fill((75, 170, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        blue_pass.set_alpha(38)

        shimmer = int(math.sin(self.frame * 0.23) * min(4, speed * 0.24))
        target.blit(red_pass, (shake_x + chromatic_shift + shimmer, shake_y), special_flags=pygame.BLEND_RGBA_ADD)
        target.blit(blue_pass, (shake_x - chromatic_shift, shake_y), special_flags=pygame.BLEND_RGBA_ADD)
        target.blit(source_view, (shake_x, shake_y))

        if not game_over:
            self.snow.draw(target, speed)
            self._draw_glitch_bars(target)
            self._draw_noise(target, speed)
        target.blit(self.scanlines, (0, 0))
        target.blit(self.vignette, (0, 0))

        if self.pulse_alpha:
            pulse = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pulse.fill((255, 255, 255, self.pulse_alpha))
            target.blit(pulse, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if self.laser_alpha and not game_over:
            laser_flash = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            laser_flash.fill((255, 32, 96, self.laser_alpha))
            target.blit(laser_flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if self.flash_alpha:
            flash = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            flash.fill((255, 78, 54, self.flash_alpha))
            target.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _shake_offset(self) -> tuple[int, int]:
        if self.shake_amount <= 0:
            return 0, 0

        amount = int(self.shake_amount)
        return random.randint(-amount, amount), random.randint(-amount, amount)

    def _draw_speed_lines(self, target: pygame.Surface, speed: float) -> None:
        if speed < 7:
            return

        alpha = min(95, int((speed - 7) * 19))
        line_count = min(22, int(speed * 1.8))
        line_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        for index in range(line_count):
            y = (index * 41 + self.frame * 7) % self.height
            x = (index * 113 + self.frame * 23) % self.width
            length = 46 + int(speed * 5)
            pygame.draw.line(line_surface, (180, 245, 233, alpha), (x, y), (x - length, y + 2), 2)

        target.blit(line_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_glitch_bars(self, target: pygame.Surface) -> None:
        if self.glitch_frames <= 0:
            return

        snapshot = target.copy()
        for _ in range(9):
            y = random.randint(45, self.height - 45)
            height = random.randint(4, 18)
            shift = random.randint(-26, 26)
            source_rect = pygame.Rect(0, y, self.width, height)
            target.blit(snapshot, (shift, y), source_rect)

        tint = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        tint.fill((255, 255, 255, 10 + self.glitch_frames))
        target.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_noise(self, target: pygame.Surface, speed: float) -> None:
        if speed < 8 and self.glitch_frames <= 0:
            return

        noise = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        speck_count = min(130, 24 + int(speed * 7) + self.glitch_frames * 3)
        for _ in range(speck_count):
            x = random.randrange(0, self.width)
            y = random.randrange(0, self.height)
            alpha = random.randint(18, 62)
            noise.set_at((x, y), (255, 255, 255, alpha))

        target.blit(noise, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)


