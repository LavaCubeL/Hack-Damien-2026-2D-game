import pygame
import pygame_menu
import main

pygame.init()
surface = pygame.display.set_mode((600, 400))

def start_the_game():
    # Do the job here !
    main.main()
    
    # After run_game() finishes, we need to reset the display 
    # so the menu looks correct when we return
    pygame.display.set_mode((600, 400))
    pass

menu = pygame_menu.Menu('Welcome', 400, 300,
                       theme=pygame_menu.themes.THEME_BLUE)

menu.add.button('Play', start_the_game)
menu.add.button('Quit', pygame_menu.events.EXIT)

# Run menu
menu.mainloop(surface)