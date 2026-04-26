"""Boss encounter classes.

Each encounter reports simple event strings back to Game so the main loop
can decide how to spawn hazards or trigger screen effects.
"""

from __future__ import annotations

import math
import random

import pygame

from settings import (
    ACCENT,
    BOSS,
    BOSS_DARK,
    FLOOR_Y,
    HAZARD,
    LASER_CORE,
    LAVA,
    RHYTHM_DEBUG,
    TEXT,
    VOID,
    WIDTH,
)


class BossEncounter:
    """Optional boss that interrupts the cave with screen flips and explosives."""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.x = WIDTH + 180
        self.target_x = WIDTH - 145
        self.age = 0
        self.attack_timer = 118
        self.done = False
        self.dialogue = "DODGE THIS"
        self.dialogue_timer = 160
        self.hand_phase = random.random() * math.tau

    def update(self, speed: float) -> list[str]:
        self.age += 1
        self.dialogue_timer = max(0, self.dialogue_timer - 1)

        if self.x > self.target_x:
            self.x -= round(speed * 1.6)
            return []

        self.attack_timer -= 1
        events: list[str] = []
        if self.attack_timer <= 0:
            if random.random() < 0.45:
                self.dialogue = "LEFT IS RIGHT"
                self.dialogue_timer = 125
                events.append("flip")
            else:
                self.dialogue = "DODGE THIS"
                self.dialogue_timer = 125
                events.append("explosive")

            self.attack_timer = random.randint(118, 168)

        if self.age > 1350:
            self.done = True

        return events

    def draw(self, screen: pygame.Surface) -> None:
        bob = int(math.sin(self.age * 0.045) * 10)
        body_rect = pygame.Rect(int(self.x), 92 + bob, 116, 126)
        left_hand = (int(self.x - 36), 242 + int(math.sin(self.age * 0.08 + self.hand_phase) * 24))
        right_hand = (int(self.x + 122), 236 + int(math.cos(self.age * 0.08 + self.hand_phase) * 24))

        pygame.draw.ellipse(screen, BOSS_DARK, body_rect.inflate(26, 22))
        pygame.draw.rect(screen, BOSS, body_rect, border_radius=18)
        pygame.draw.circle(screen, LASER_CORE, (body_rect.left + 35, body_rect.top + 43), 9)
        pygame.draw.circle(screen, LASER_CORE, (body_rect.left + 81, body_rect.top + 43), 9)
        pygame.draw.rect(screen, HAZARD, (body_rect.left + 35, body_rect.top + 86, 47, 8), border_radius=3)

        self._draw_hand(screen, left_hand, -1)
        self._draw_hand(screen, right_hand, 1)

        if self.dialogue_timer > 0:
            self._draw_dialogue(screen, body_rect)

    def _draw_hand(self, screen: pygame.Surface, center: tuple[int, int], side: int) -> None:
        pygame.draw.line(screen, BOSS_DARK, (int(self.x + 58), 177), center, 14)
        palm = pygame.Rect(0, 0, 54, 42)
        palm.center = center
        pygame.draw.ellipse(screen, BOSS, palm)
        for index in range(3):
            finger = pygame.Rect(0, 0, 15, 28)
            finger.center = (center[0] + side * (13 + index * 8), center[1] - 14 + index * 4)
            pygame.draw.ellipse(screen, BOSS, finger)

    def _draw_dialogue(self, screen: pygame.Surface, body_rect: pygame.Rect) -> None:
        text = self.font.render(self.dialogue, True, TEXT)
        bubble = text.get_rect()
        bubble.inflate_ip(28, 18)
        bubble.midbottom = (body_rect.centerx - 28, body_rect.top - 12)
        pygame.draw.rect(screen, (10, 11, 18), bubble, border_radius=7)
        pygame.draw.rect(screen, HAZARD, bubble, 2, border_radius=7)
        screen.blit(text, text.get_rect(center=bubble.center))


class RhythmBossEncounter:
    """Osu-inspired boss where timed jump hits prevent lava attacks."""

    # Rhythm tuning: the moving circle reaches the player exactly at HIT_FRAME.
    HIT_FRAME = 82
    PERFECT_WINDOW = 8
    GOOD_WINDOW = 20
    MISS_GRACE_FRAMES = 34
    PLAYER_STANDING_CENTER = (130, FLOOR_Y - 31)
    PROMPT_START_X = WIDTH - 120

    FEEDBACK_COLORS = {
        "PERFECT": LASER_CORE,
        "GOOD": ACCENT,
        "BAD": HAZARD,
        "MISS": HAZARD,
    }

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.age = 0
        self.x = WIDTH + 210
        self.target_x = WIDTH - 170
        self.done = False
        self.dialogue = "JUMP IN THE CIRCLE"
        self.dialogue_timer = 190
        self.feedback = ""
        self.feedback_timer = 0
        self.prompt_timer = 115
        # The prompt stays alive after the hit frame so a slightly late tap can be judged.
        self.prompt_duration = self.HIT_FRAME + self.MISS_GRACE_FRAMES
        self.prompt_age = 0
        self.prompt_active = False
        self.target_center = (self.PROMPT_START_X, self.PLAYER_STANDING_CENTER[1])
        self.target_radius = 46
        self.approach_start_radius = 150
        self.successes = 0
        self.total_prompts = 0

    def update(self, speed: float, player_rect: pygame.Rect) -> list[str]:
        self.age += 1
        self.dialogue_timer = max(0, self.dialogue_timer - 1)
        self.feedback_timer = max(0, self.feedback_timer - 1)

        if self.x > self.target_x:
            self.x -= round(speed * 1.4)
            return []

        events: list[str] = []
        if self.prompt_active:
            self.prompt_age += 1
            self.target_center = self._prompt_center()
            if self.prompt_age >= self.prompt_duration:
                self._set_feedback("MISS")
                self.prompt_active = False
                self.prompt_timer = 74
                if RHYTHM_DEBUG:
                    print(f"rhythm miss: age={self.prompt_age}, hit_frame={self.HIT_FRAME}")
                events.append("lava")
        else:
            self.prompt_timer -= 1
            if self.prompt_timer <= 0:
                self._start_prompt()

        if self.total_prompts >= 8 and not self.prompt_active and self.feedback_timer == 0:
            self.done = True

        return events

    def handle_jump(self, player_rect: pygame.Rect) -> str | None:
        if not self.prompt_active:
            return None

        self.target_center = self._prompt_center()
        dx = player_rect.centerx - self.target_center[0]
        dy = player_rect.centery - self.target_center[1]
        distance = math.hypot(dx, dy)
        timing_error = abs(self.prompt_age - self.HIT_FRAME)

        # A tap only succeeds when the moving circle is actually crossing the player.
        if distance > self.target_radius + 34:
            result = "BAD"
        elif timing_error <= self.PERFECT_WINDOW:
            result = "PERFECT"
        elif timing_error <= self.GOOD_WINDOW:
            result = "GOOD"
        else:
            result = "BAD"

        if RHYTHM_DEBUG:
            print(
                "rhythm tap: "
                f"age={self.prompt_age}, error={timing_error}, "
                f"distance={distance:.1f}, result={result}"
            )

        self.prompt_active = False
        self.prompt_timer = 62
        self._set_feedback(result)

        if result in ("PERFECT", "GOOD"):
            self.successes += 1

        return result

    def draw(self, screen: pygame.Surface) -> None:
        bob = int(math.sin(self.age * 0.05) * 9)
        body_rect = pygame.Rect(int(self.x), 98 + bob, 128, 122)
        pygame.draw.ellipse(screen, (32, 15, 38), body_rect.inflate(36, 26))
        pygame.draw.rect(screen, VOID, body_rect, border_radius=20)
        pygame.draw.circle(screen, ACCENT, (body_rect.left + 37, body_rect.top + 42), 10)
        pygame.draw.circle(screen, ACCENT, (body_rect.left + 91, body_rect.top + 42), 10)
        pygame.draw.arc(screen, LAVA, (body_rect.left + 32, body_rect.top + 70, 64, 32), 0, math.pi, 5)

        if self.prompt_active:
            self._draw_prompt(screen)

        if self.dialogue_timer > 0:
            self._draw_bubble(screen, body_rect, self.dialogue, TEXT)

        if self.feedback_timer > 0 and self.feedback:
            color = self.FEEDBACK_COLORS.get(self.feedback, TEXT)
            self._draw_feedback(screen, color)

    def _start_prompt(self) -> None:
        self.prompt_active = True
        self.prompt_age = 0
        self.total_prompts += 1
        self.dialogue = random.choice(("TIME IT", "JUMP IN", "HIT THE CIRCLE", "STAY OFF LAVA"))
        self.dialogue_timer = 92
        # Start the prompt on the right; it will reach the player on HIT_FRAME.
        self.target_center = (self.PROMPT_START_X, self.PLAYER_STANDING_CENTER[1])

    def _set_feedback(self, result: str) -> None:
        self.feedback = result
        self.feedback_timer = 76
        self.dialogue = result
        self.dialogue_timer = 80

    def _prompt_center(self) -> tuple[int, int]:
        """Move the rhythm circle from right to left until it crosses the player."""
        hit_x, hit_y = self.PLAYER_STANDING_CENTER
        travel = hit_x - self.PROMPT_START_X
        progress = self.prompt_age / self.HIT_FRAME
        return int(self.PROMPT_START_X + travel * progress), hit_y

    def _draw_prompt(self, screen: pygame.Surface) -> None:
        self.target_center = self._prompt_center()
        center = self.target_center
        hit_progress = min(1.0, self.prompt_age / self.HIT_FRAME)
        remaining = max(0.0, 1.0 - hit_progress)
        approach_radius = int(self.target_radius + (self.approach_start_radius - self.target_radius) * remaining)
        timing_error = abs(self.prompt_age - self.HIT_FRAME)
        target_color = ACCENT if timing_error <= self.GOOD_WINDOW else TEXT
        fill_radius = int((self.target_radius - 10) * hit_progress)

        pulse = pygame.Surface((220, 220), pygame.SRCALPHA)
        # The inner fill reaches the target ring at the same frame a tap should land.
        pygame.draw.circle(pulse, (*ACCENT, 42), (110, 110), fill_radius)
        pygame.draw.circle(pulse, (*ACCENT, 36), (110, 110), max(self.target_radius, approach_radius), 4)
        pygame.draw.circle(pulse, (*target_color, 190), (110, 110), self.target_radius, 5)
        pygame.draw.circle(pulse, (0, 0, 0, 120), (110, 110), self.target_radius - 8)
        pygame.draw.circle(pulse, (*LASER_CORE, 220), (110, 110), 8)
        screen.blit(pulse, pulse.get_rect(center=center), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_bubble(self, screen: pygame.Surface, body_rect: pygame.Rect, message: str, color: tuple[int, int, int]) -> None:
        text = self.font.render(message, True, color)
        bubble = text.get_rect()
        bubble.inflate_ip(28, 18)
        bubble.midbottom = (body_rect.centerx - 34, body_rect.top - 10)
        pygame.draw.rect(screen, (10, 11, 18), bubble, border_radius=7)
        pygame.draw.rect(screen, color, bubble, 2, border_radius=7)
        screen.blit(text, text.get_rect(center=bubble.center))

    def _draw_feedback(self, screen: pygame.Surface, color: tuple[int, int, int]) -> None:
        text = self.font.render(self.feedback, True, color)
        rect = text.get_rect(center=(WIDTH // 2, 118))
        shadow = text.copy()
        shadow.fill((0, 0, 0, 160), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(shadow, rect.move(3, 3))
        screen.blit(text, rect)
