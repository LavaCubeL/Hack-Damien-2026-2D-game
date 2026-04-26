"""Shared game constants and color palette.

Every gameplay module imports values from here so window size, physics,
and colors stay consistent after the class split.
"""

from __future__ import annotations


# Window and frame-rate settings used by the Pygame loop.
WIDTH = 960
HEIGHT = 540
FPS = 60

# Core movement and world tuning.
FLOOR_Y = 430
GRAVITY = 0.85
JUMP_SPEED = -17
START_SPEED = 6

# Scene and sprite colors.
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
