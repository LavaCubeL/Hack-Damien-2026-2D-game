"""OOP cave side-scroller prototype built with Pygame.

Controls:
    Space / Up / W: jump / double jump
    Down / S: fast fall
    F: toggle screen effects
    R: restart after game over
    Esc: quit
"""

from __future__ import annotations

import math
import queue
import random
import threading
import time
from dataclasses import dataclass

import pygame


WIDTH = 960
HEIGHT = 540
FPS = 60

FLOOR_Y = 430
GRAVITY = 0.85
JUMP_SPEED = -17
START_SPEED = 6

SKY = (16, 18, 28)
STONE = (62, 65, 78)
STONE_DARK = (40, 42, 54)
GROUND = (83, 77, 71)
GROUND_DARK = (44, 42, 44)
PLAYER = (236, 207, 98)
PLAYER_DARK = (166, 128, 47)
ROCK = (124, 119, 111)
ROCK_DARK = (83, 80, 78)
TEXT = (238, 236, 225)
ACCENT = (117, 192, 179)
HAZARD = (205, 91, 75)
LASER = (255, 42, 86)
LASER_CORE = (255, 238, 186)
VOID = (68, 47, 94)
BOSS = (105, 69, 132)
BOSS_DARK = (46, 32, 67)
EXPLOSIVE = (235, 78, 58)
LAVA = (240, 74, 40)
LAVA_CORE = (255, 198, 72)
SNOW = (218, 243, 255)


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
        pygame.draw.rect(surface, PLAYER, (10, 14, 32, 35), border_radius=4)
        pygame.draw.rect(surface, PLAYER, (25, 0, 24, 22), border_radius=4)
        pygame.draw.rect(surface, PLAYER_DARK, (13, 48, 8, 14))
        pygame.draw.rect(surface, PLAYER_DARK, (32, 48, 8, 14))
        pygame.draw.rect(surface, PLAYER_DARK, (0, 26, 16, 9), border_radius=3)
        pygame.draw.circle(surface, STONE_DARK, (41, 8), 3)
        pygame.draw.rect(surface, TEXT, (43, 18, 8, 4), border_radius=2)
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
        self.prompt_duration = 118
        self.prompt_age = 0
        self.prompt_active = False
        self.target_center = (145, 305)
        self.target_radius = 43
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
            if self.prompt_age >= self.prompt_duration:
                self._set_feedback("MISS")
                self.prompt_active = False
                self.prompt_timer = 74
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

        dx = player_rect.centerx - self.target_center[0]
        dy = player_rect.centery - self.target_center[1]
        distance = math.hypot(dx, dy)
        timing_error = abs(self.prompt_age - 78)

        if distance > self.target_radius + 28:
            result = "BAD"
        elif timing_error <= 7:
            result = "PERFECT"
        elif timing_error <= 17:
            result = "GOOD"
        else:
            result = "BAD"

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
        self.target_center = (145, random.choice((285, 335, 365)))

    def _set_feedback(self, result: str) -> None:
        self.feedback = result
        self.feedback_timer = 76
        self.dialogue = result
        self.dialogue_timer = 80

    def _draw_prompt(self, screen: pygame.Surface) -> None:
        center = self.target_center
        progress = self.prompt_age / self.prompt_duration
        approach_radius = int(155 - progress * 112)
        target_color = ACCENT if abs(self.prompt_age - 78) <= 17 else TEXT

        pulse = pygame.Surface((220, 220), pygame.SRCALPHA)
        pygame.draw.circle(pulse, (*ACCENT, 36), (110, 110), max(10, approach_radius), 4)
        pygame.draw.circle(pulse, (*target_color, 180), (110, 110), self.target_radius, 5)
        pygame.draw.circle(pulse, (0, 0, 0, 120), (110, 110), self.target_radius - 8)
        pygame.draw.circle(pulse, (*LASER_CORE, 210), (110, 110), 8)
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


class EventDirector:
    """Background event scheduler.

    This thread never touches Pygame objects. It only asks the main loop to
    consider a random event, which keeps rendering and sprite state stable.
    """

    def __init__(self, outbox: queue.Queue[str]) -> None:
        self.outbox = outbox
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            time.sleep(random.uniform(1.2, 2.8))
            try:
                self.outbox.put_nowait("random_event")
            except queue.Full:
                pass


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
        self.flash_alpha = 150
        self.shake_amount = 16

    def trigger_laser(self) -> None:
        self.laser_alpha = 180
        self.glitch_frames = 24
        self.shake_amount = max(self.shake_amount, 20)

    def trigger_event_pulse(self) -> None:
        self.pulse_alpha = 95
        self.glitch_frames = max(self.glitch_frames, 8)
        self.shake_amount = max(self.shake_amount, 3)

    def trigger_screen_flip(self) -> None:
        self.mirror_frames = 150
        self.glitch_frames = max(self.glitch_frames, 28)
        self.pulse_alpha = 135
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
            pulse.fill((82, 255, 220, self.pulse_alpha))
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
        tint.fill((90, 255, 230, 18 + self.glitch_frames * 2))
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


class Game:
    """Owns the main loop and coordinates every object."""

    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.scene = pygame.Surface((WIDTH, HEIGHT)).convert()
        pygame.display.set_caption("Cave Runner Prototype")
        self.clock = pygame.time.Clock()
        self.background = Background()
        self.hud = Hud()
        self.event_font = pygame.font.Font(None, 38)
        self.shader = ScreenShader((WIDTH, HEIGHT))
        self.event_requests: queue.Queue[str] = queue.Queue(maxsize=12)
        self.event_director = EventDirector(self.event_requests)
        self.event_director.start()
        self.running = True
        self.reset()

    def reset(self) -> None:
        self.speed = START_SPEED
        self.score = 0
        self.game_over = False
        self.player = Player(130, FLOOR_Y)
        self.player_group = pygame.sprite.GroupSingle(self.player)
        self.obstacles = pygame.sprite.Group()
        self.falling_rocks = pygame.sprite.Group()
        self.explosives = pygame.sprite.Group()
        self.relics = pygame.sprite.Group()
        self.floating_texts: list[FloatingText] = []
        self.lasers: list[LaserBeam] = []
        self.boss: BossEncounter | None = None
        self.rhythm_boss: RhythmBossEncounter | None = None
        self.boss_roll_checked = False
        self.rhythm_boss_spawned = False
        self.lava_timer = 0
        self.ground = pygame.sprite.Group(GroundChunk(0, FLOOR_Y, WIDTH), GroundChunk(WIDTH, FLOOR_Y, WIDTH))
        self.ceiling = pygame.sprite.Group(CeilingChunk(0, WIDTH), CeilingChunk(WIDTH, WIDTH))
        self.obstacle_timer = SpawnTimer(55, 105)
        self.rock_timer = SpawnTimer(90, 155)
        self.laser_cooldown = 260
        self.hazard_pause = 0
        self.obstacle_timer.reset()
        self.rock_timer.reset()
        self._clear_event_requests()

    def run(self) -> None:
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(FPS)
        finally:
            self.event_director.stop()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self.player.jump()
                    self._judge_rhythm_jump()
                elif event.key == pygame.K_r and self.game_over:
                    self.reset()
                elif event.key == pygame.K_f:
                    self.shader.enabled = not self.shader.enabled

        keys = pygame.key.get_pressed()
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player.fast_fall()

    def update(self) -> None:
        if self.game_over:
            self.shader.update(self.speed, self.game_over)
            return

        self.speed += 0.0028
        self.score += 1
        self.laser_cooldown = max(0, self.laser_cooldown - 1)
        self.hazard_pause = max(0, self.hazard_pause - 1)
        self.lava_timer = max(0, self.lava_timer - 1)
        self.shader.update(self.speed, self.game_over)
        self._check_boss_spawn()
        self._check_rhythm_boss_spawn()
        self._process_event_requests()
        self.background.update(self.speed)
        self.player_group.update()
        self.obstacles.update(self.speed)
        self.falling_rocks.update()
        self.explosives.update(self.speed)
        self.relics.update(self.speed)
        self._update_floating_texts()
        self._update_lasers()
        self._update_boss()
        self._update_rhythm_boss()

        if self.hazard_pause == 0 and not self._encounter_active:
            if self.obstacle_timer.tick():
                self.obstacles.add(Obstacle(WIDTH + 50, FLOOR_Y, self.speed))
                self.obstacle_timer.reset()

            if self.rock_timer.tick():
                self.falling_rocks.add(FallingRock(WIDTH + 30, self.speed))
                self.rock_timer.reset()

        self._scroll_chunks(self.ground, GroundChunk, FLOOR_Y)
        self._scroll_chunks(self.ceiling, CeilingChunk)

        if pygame.sprite.spritecollide(self.player, self.obstacles, False, pygame.sprite.collide_mask):
            self._crash()

        if pygame.sprite.spritecollide(self.player, self.falling_rocks, False, pygame.sprite.collide_mask):
            self._crash()

        if any(laser.collides_with(self.player.rect) for laser in self.lasers):
            self._crash()

        if any(explosive.collides_with(self.player.rect) for explosive in self.explosives):
            self._crash()

        if self.lava_timer > 0 and self.player.rect.bottom >= FLOOR_Y - 3:
            self._crash()

    @property
    def _boss_active(self) -> bool:
        return self.boss is not None and not self.boss.done

    @property
    def _rhythm_active(self) -> bool:
        return self.rhythm_boss is not None and not self.rhythm_boss.done

    @property
    def _encounter_active(self) -> bool:
        return self._boss_active or self._rhythm_active

    def _check_boss_spawn(self) -> None:
        if self.boss_roll_checked or self.score < 2500:
            return

        self.boss_roll_checked = True
        if not self._rhythm_active and random.random() < 0.5:
            self._spawn_boss()

    def _spawn_boss(self) -> None:
        self.boss = BossEncounter(self.event_font)
        self.lasers.clear()
        self.floating_texts.clear()
        self.obstacles.empty()
        self.falling_rocks.empty()
        self.hazard_pause = 220
        self.laser_cooldown = 9999
        self.shader.trigger_event_pulse()

    def _check_rhythm_boss_spawn(self) -> None:
        if self.rhythm_boss_spawned or self.score < 5000 or self._boss_active:
            return

        self.rhythm_boss_spawned = True
        self._spawn_rhythm_boss()

    def _spawn_rhythm_boss(self) -> None:
        self.rhythm_boss = RhythmBossEncounter(self.event_font)
        self.lasers.clear()
        self.floating_texts.clear()
        self.obstacles.empty()
        self.falling_rocks.empty()
        self.explosives.empty()
        self.hazard_pause = 260
        self.laser_cooldown = 9999
        self.lava_timer = 0
        self.shader.trigger_event_pulse()

    def _clear_event_requests(self) -> None:
        while True:
            try:
                self.event_requests.get_nowait()
            except queue.Empty:
                return

    def _process_event_requests(self) -> None:
        processed = 0
        while processed < 4:
            try:
                self.event_requests.get_nowait()
            except queue.Empty:
                return

            self._spawn_random_event()
            processed += 1

    def _spawn_random_event(self) -> None:
        if self.hazard_pause > 0 or self._encounter_active:
            return

        level = self.score // 650
        roll = random.random()

        if level <= 0:
            if roll < 0.6:
                self._spawn_floating_text()
            else:
                self._spawn_relic()
            return

        if level < 3:
            if roll < 0.38:
                self._spawn_floating_text()
            elif roll < 0.78:
                self._spawn_relic()
            else:
                self.falling_rocks.add(FallingRock(WIDTH + 30, self.speed))
            return

        if not self._encounter_active and self.laser_cooldown == 0 and roll < min(0.36, 0.18 + level * 0.025):
            self._spawn_laser()
        elif roll < 0.42:
            self._spawn_floating_text()
        elif roll < 0.78:
            self._spawn_relic()
        else:
            self.falling_rocks.add(FallingRock(WIDTH + 30, self.speed))

    def _spawn_floating_text(self) -> None:
        self.floating_texts.append(FloatingText(self.event_font, self.score))
        self.shader.trigger_event_pulse()

    def _spawn_relic(self) -> None:
        y = random.randint(115, 360)
        self.relics.add(CaveRelic(WIDTH + 50, y, self.speed))
        self.shader.trigger_event_pulse()

    def _spawn_laser(self) -> None:
        y = random.choice((286, 386))
        self._prepare_laser_lane()
        self.lasers.append(LaserBeam(y))
        self.floating_texts.append(FloatingText(self.event_font, self.score))
        self.hazard_pause = 150
        self.obstacle_timer.value = max(self.obstacle_timer.value, 150)
        self.rock_timer.value = max(self.rock_timer.value, 120)
        self.laser_cooldown = random.randint(340, 520)
        self.shader.trigger_event_pulse()

    def _prepare_laser_lane(self) -> None:
        danger_zone = pygame.Rect(self.player.rect.left - 60, 0, WIDTH + 240, HEIGHT)

        for obstacle in list(self.obstacles):
            if obstacle.rect.colliderect(danger_zone):
                obstacle.kill()

        for falling_rock in list(self.falling_rocks):
            if falling_rock.rect.centerx > self.player.rect.centerx - 80:
                falling_rock.kill()

    def _update_floating_texts(self) -> None:
        for floating_text in self.floating_texts:
            floating_text.update(self.speed)

        self.floating_texts = [floating_text for floating_text in self.floating_texts if floating_text.alive]

    def _update_lasers(self) -> None:
        if self._encounter_active:
            self.lasers.clear()
            return

        for laser in self.lasers:
            was_active = laser.active
            laser.update()
            if laser.active and not was_active:
                self.shader.trigger_laser()

        self.lasers = [laser for laser in self.lasers if not laser.done]

    def _update_boss(self) -> None:
        if self.boss is None:
            return

        self.hazard_pause = max(self.hazard_pause, 2)
        self.laser_cooldown = max(self.laser_cooldown, 180)

        for event in self.boss.update(self.speed):
            if event == "flip":
                self.shader.trigger_screen_flip()
            elif event == "explosive":
                self._spawn_boss_explosives()

        if self.boss.done:
            self.boss = None
            self.hazard_pause = 120
            self.laser_cooldown = 280

    def _update_rhythm_boss(self) -> None:
        if self.rhythm_boss is None:
            return

        self.hazard_pause = max(self.hazard_pause, 2)
        self.laser_cooldown = max(self.laser_cooldown, 180)

        for event in self.rhythm_boss.update(self.speed, self.player.rect):
            if event == "lava":
                self._trigger_lava()

        if self.rhythm_boss.done:
            self.rhythm_boss = None
            self.hazard_pause = 140
            self.laser_cooldown = 320
            self.lava_timer = 0

    def _judge_rhythm_jump(self) -> None:
        if self.rhythm_boss is None or self.rhythm_boss.done:
            return

        result = self.rhythm_boss.handle_jump(self.player.rect)
        if result is None:
            return

        if result in ("PERFECT", "GOOD"):
            self.shader.trigger_event_pulse()
        else:
            self._trigger_lava()

    def _trigger_lava(self) -> None:
        self.lava_timer = 118
        if self.rhythm_boss is not None:
            self.rhythm_boss.prompt_active = False
            self.rhythm_boss.prompt_timer = max(self.rhythm_boss.prompt_timer, 135)
        self.shader.trigger_event_pulse()
        self.shader.trigger_impact()

    def _spawn_boss_explosives(self) -> None:
        count = 2 if random.random() < 0.35 else 1
        lanes = random.sample((540, 650, 760, 870), count)

        for x in lanes:
            self.explosives.add(Explosive(x, self.speed))

        self.shader.trigger_event_pulse()

    def _scroll_chunks(self, group: pygame.sprite.Group, chunk_type: type[pygame.sprite.Sprite], *args: int) -> None:
        for chunk in group:
            chunk.update(self.speed)

        chunks = sorted(group.sprites(), key=lambda sprite: sprite.rect.x)
        if chunks and chunks[0].rect.right <= 0:
            chunks[0].kill()
            right_edge = max(sprite.rect.right for sprite in group)
            if chunk_type is GroundChunk:
                group.add(GroundChunk(right_edge, FLOOR_Y, WIDTH))
            else:
                group.add(CeilingChunk(right_edge, WIDTH))

    def _crash(self) -> None:
        if self.game_over:
            return

        self.game_over = True
        self.player.alive = False
        self.floating_texts.clear()
        self.relics.empty()
        self.lasers.clear()
        self.explosives.empty()
        self.boss = None
        self.rhythm_boss = None
        self.lava_timer = 0
        self.shader.trigger_impact()

    def draw(self) -> None:
        self.background.draw(self.scene)
        self.ceiling.draw(self.scene)
        self.ground.draw(self.scene)
        if self.lava_timer > 0 and not self.game_over:
            self._draw_lava(self.scene)
        if self.boss is not None and not self.game_over:
            self.boss.draw(self.scene)
        if self.rhythm_boss is not None and not self.game_over:
            self.rhythm_boss.draw(self.scene)
        if not self.game_over:
            self.relics.draw(self.scene)
        self.obstacles.draw(self.scene)
        self.falling_rocks.draw(self.scene)
        if not self.game_over:
            self.explosives.draw(self.scene)
        if not self.game_over:
            for laser in self.lasers:
                laser.draw(self.scene)
            for floating_text in self.floating_texts:
                floating_text.draw(self.scene)
        self.player_group.draw(self.scene)
        self.shader.apply(self.scene, self.screen, self.speed, self.game_over)
        self.hud.draw(self.screen, self.score, self.speed, self.game_over)
        pygame.display.flip()

    def _draw_lava(self, screen: pygame.Surface) -> None:
        lava = pygame.Surface((WIDTH, HEIGHT - FLOOR_Y + 18), pygame.SRCALPHA)
        alpha = min(230, 90 + self.lava_timer)
        lava.fill((*LAVA, alpha))

        for x in range(-40, WIDTH + 40, 56):
            wave_y = 12 + int(math.sin((self.shader.frame + x) * 0.055) * 7)
            pygame.draw.circle(lava, (*LAVA_CORE, 170), (x, wave_y), 28)
            pygame.draw.circle(lava, (255, 104, 54, 120), (x + 24, wave_y + 12), 18)

        pygame.draw.line(lava, (*LAVA_CORE, 210), (0, 7), (WIDTH, 7), 4)
        screen.blit(lava, (0, FLOOR_Y - 10), special_flags=pygame.BLEND_RGBA_ADD)
