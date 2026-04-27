# Cave Runner Prototype

A basic OOP Python/Pygame side scroller inspired by the offline dinosaur game. The player runs through a cave, jumps over ground obstacles, dodges falling rocks, and the game gets faster over time.

As your score gets higher, the cave starts triggering random events:

- Floating warning text
- Random cave relics, eyes, and glitchy objects
- Extra falling rocks
- Laser warnings followed by damaging laser beams
- Laser screen shake, red flash, chromatic split, glitch bars, noise, and pulse effects
- Layered snow/ash particles instead of simple line-only speed effects

Laser events briefly clear nearby hazards and pause new obstacle spawns so the player is not trapped between a laser and an unavoidable obstacle.

At 2500 meters, the game rolls a one-time 50% chance to spawn a boss. If the boss appears, lasers stop during the encounter. The boss has two hands, dialogue, screen-flip attacks, and explosive hazards that warn before they detonate.

At 5000 meters, a second rhythm boss starts an osu-inspired jump-circle section. Jump while inside the timing circle to earn `PERFECT` or `GOOD`. A `BAD` or missed circle turns the ground into lava for a short dodge window.

## Run

```powershell
download the project
run the main.exe in the dist folder
```

## Controls

- `Space`, `Up`, or `W`: jump / double jump
- `Down` or `S`: fast fall
- `F`: toggle screen shader effects
- `R`: restart after crashing
- `Esc`: quit

## Structure

- `main.py`: small entry point
- `game.py`: OOP game classes for the player, obstacles, falling rocks, lasers, boss encounters, rhythm circles, explosives, lava, cave chunks, random events, screen shader effects, HUD, and main game loop

The prototype uses simple generated sprite surfaces, so there are no external image assets required.

## Threading Note

The prototype uses a small background `EventDirector` thread to schedule random event requests. The thread does not touch Pygame surfaces, sprites, input, or rendering. Those stay on the main thread because moving Pygame drawing or sprite mutation into worker threads can cause unstable behavior.
