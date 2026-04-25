import sys


try:
    import pygame
except ModuleNotFoundError:
    print("pygame is not installed for this Python environment.")
    print("Install it with: python3 -m pip install pygame")
    sys.exit(1)


WIDTH = 800
HEIGHT = 450
FPS = 60


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pygame Smoke Test")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)

    ball_x = WIDTH // 2
    ball_y = HEIGHT // 2
    ball_speed_x = 5
    ball_speed_y = 4
    ball_radius = 28

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        ball_x += ball_speed_x
        ball_y += ball_speed_y

        if ball_x - ball_radius <= 0 or ball_x + ball_radius >= WIDTH:
            ball_speed_x *= -1
        if ball_y - ball_radius <= 0 or ball_y + ball_radius >= HEIGHT:
            ball_speed_y *= -1

        screen.fill((24, 28, 36))
        pygame.draw.circle(screen, (70, 190, 255), (ball_x, ball_y), ball_radius)

        label = font.render("Pygame works - press Esc to quit", True, (240, 240, 240))
        screen.blit(label, (24, 24))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
