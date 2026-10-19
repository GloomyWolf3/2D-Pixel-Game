# scripts/config/settings.py

# --- Окно ---
GAME_TITLE = "Terraria-like"
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# --- Мир ---
TILE_SIZE = 16
CHUNK_SIZE = 16

# Размеры миров (в тайлах): (ширина, высота)
WORLD_SIZES = {
    "small":  (1200, 400),
    "medium": (2400, 600),
    "large":  (4200, 800),
}

# --- День/ночь ---
DAY_DURATION_SECONDS = 180.0
START_TIME_OF_DAY = 0.30

# --- Пути ---
SAVES_DIR = "saves"
LOG_DIR = "logs"
TEXTURES_DIR = "assets/textures"

# --- Читы (изменяются в настройках) ---
CHEATS_ENABLED = False

# --- Цвета (пиксельная палитра) ---
COLOR_BG          = (18, 20, 30)
COLOR_BG_DARK     = (10, 12, 20)
COLOR_STAR        = (200, 210, 240)

COLOR_TEXT        = (232, 232, 232)
COLOR_TEXT_DIM    = (150, 150, 160)
COLOR_TEXT_INPUT  = (255, 255, 255)

COLOR_ACCENT      = (140, 210, 130)
COLOR_ACCENT_HOVER= (180, 240, 160)
COLOR_ACCENT_DARK = (70, 130, 70)

COLOR_BUTTON      = (42, 46, 62)
COLOR_BUTTON_HOVER= (66, 72, 96)
COLOR_BORDER      = (110, 118, 140)

COLOR_DANGER      = (170, 70, 70)
COLOR_DANGER_HOVER= (210, 90, 90)

COLOR_PANEL       = (26, 28, 40)
COLOR_PANEL_BORDER= (70, 78, 100)


def get_font(size: int, bold: bool = False):
    """Единая функция получения шрифта с поддержкой кириллицы."""
    import pygame
    return pygame.font.SysFont(
        "consolas,dejavusansmono,liberationmono,couriernew,arial",
        size, bold=bold
    )
