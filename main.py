# main.py
import sys
import pygame

from scripts.config import settings
from scripts.utils import file_utils
from scripts.game_logic.menu import Menu
from scripts.game_logic.game import Game


def main() -> None:
    file_utils.ensure_dirs()

    pygame.init()
    pygame.display.set_caption(settings.GAME_TITLE)

    screen = pygame.display.set_mode(
        (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
    )
    pygame.display.set_icon(
        pygame.Surface((32, 32))  # заглушка, заменим иконкой
    )

    while True:
        menu = Menu(screen)
        save_folder = menu.run()

        if save_folder is None:
            # Пользователь вышел
            break

        # Пользователь выбрал сохранение -> запускаем игру
        game = Game(screen, save_folder)
        result = game.run()

        if result == "quit":
            break
        # result == "menu" — возвращаемся в меню

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
    
    