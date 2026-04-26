"""Main game coordinator for the cave runner prototype.

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

import pygame

from encounters import BossEncounter, RhythmBossEncounter
from event_director import EventDirector
from floating_text import FloatingText
from hazards import Explosive, LaserBeam
from hud import Hud
from scenery import Background
from settings import FLOOR_Y, FPS, HEIGHT, LAVA, LAVA_CORE, START_SPEED, WIDTH
from shader import ScreenShader
from spawn_timer import SpawnTimer
from sprites import CaveRelic, CeilingChunk, FallingRock, GroundChunk, Obstacle, Player


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
