"""Entry point for the cave runner prototype."""

import sys

import pygame

from game import Game


def main() -> None:
    pygame.init()
    game = Game()
    game.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
cd 