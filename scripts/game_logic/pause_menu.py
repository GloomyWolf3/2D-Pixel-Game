# scripts/game_logic/pause_menu.py
"""Пауза, настройки, меню генератора."""
from __future__ import annotations

import pygame

from scripts.config import settings
from scripts.texture_gen import library


# ---------------------------------------------------------------------------
# Общие UI-компоненты
# ---------------------------------------------------------------------------

class _Button:
    def __init__(self, rect, text, callback, font,
                 danger=False, enabled=True):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font = font
        self.base = (settings.COLOR_DANGER if danger
                     else settings.COLOR_BUTTON)
        self.hover = (settings.COLOR_DANGER_HOVER if danger
                      else settings.COLOR_BUTTON_HOVER)
        self.enabled = enabled
        self.hovered = False

    def handle(self, event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False

    def draw(self, surface):
        color = self.hover if self.hovered else self.base
        if not self.enabled:
            color = tuple(c // 2 for c in color)
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, settings.COLOR_BORDER, self.rect, 2,
                         border_radius=4)
        c = settings.COLOR_TEXT if self.enabled else settings.COLOR_TEXT_DIM
        s = self.font.render(self.text, True, c)
        surface.blit(s, s.get_rect(center=self.rect.center))


# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

class SettingsScreen:
    """Экран настроек с выбором паков блоков и деревьев."""

    def __init__(self, screen: pygame.Surface, game,
                 background: pygame.Surface | None = None):
        self.screen = screen
        self.game = game
        self.background = background
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_h1 = settings.get_font(28, bold=True)
        self.font_h2 = settings.get_font(18, bold=True)
        self.font_med = settings.get_font(16)
        self.font_small = settings.get_font(14)

        self.block_sets = library.list_sets()
        self.tree_sets = []
        try:
            from scripts.texture_gen import tree_library
            self.tree_sets = tree_library.list_tree_sets()
        except Exception:
            pass

        self.cheats = settings.CHEATS_ENABLED
        self.toast = ""
        self.toast_timer = 0.0

        self._build_buttons()
        self._layout_pack_rows()

    def _build_buttons(self) -> None:
        cx = settings.SCREEN_WIDTH // 2
        self.buttons = [
            _Button((settings.SCREEN_WIDTH - 160, 16, 140, 40),
                    "← Назад", self._close, self.font_med),
            _Button((cx - 100, settings.SCREEN_HEIGHT - 80, 200, 44),
                    "Обновить текстуры", self._reload_resources, self.font_med),
        ]

    def _layout_pack_rows(self) -> None:
        self.block_rows: list[pygame.Rect] = []
        for i in range(len(self.block_sets)):
            self.block_rows.append(pygame.Rect(60, 200 + i * 30, 350, 26))

        self.tree_rows: list[pygame.Rect] = []
        for i in range(len(self.tree_sets)):
            self.tree_rows.append(pygame.Rect(480, 200 + i * 30, 350, 26))

    def _close(self) -> None:
        self.running = False

    def _reload_resources(self) -> None:
        self.game.reload_resources()
        self._toast("Текстуры успешно обновлены!")

    def _toast(self, text: str) -> None:
        self.toast = text
        self.toast_timer = 2.0

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.event.post(event)
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self._handle(event)
            if self.toast_timer > 0:
                self.toast_timer -= dt
            self._draw()
            pygame.display.flip()

    def _handle(self, event) -> None:
        for b in self.buttons:
            b.handle(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # --- Клики по пакам блоков ---
            for i, rect in enumerate(self.block_rows):
                if rect.collidepoint(event.pos) and i < len(self.block_sets):
                    library.set_active(self.block_sets[i])
                    self.game.reload_resources() # Авто-обновление
                    self._toast(f"Блоки: {self.block_sets[i]}")
                    return
            if self._off_blocks_rect().collidepoint(event.pos):
                library.set_active(None)
                self.game.reload_resources()
                self._toast("Блоки: процедурные")
                return

            # --- Клики по пакам деревьев ---
            from scripts.texture_gen import tree_library
            for i, rect in enumerate(self.tree_rows):
                if rect.collidepoint(event.pos) and i < len(self.tree_sets):
                    tree_library.set_active(self.tree_sets[i])
                    self.game.reload_resources()
                    self._toast(f"Деревья: {self.tree_sets[i]}")
                    return
            if self._off_trees_rect().collidepoint(event.pos):
                tree_library.set_active(None)
                self.game.reload_resources()
                self._toast("Деревья: стандартные")
                return

            # Чекбокс читов
            if self._cheats_rect().collidepoint(event.pos):
                self.cheats = not self.cheats
                settings.CHEATS_ENABLED = self.cheats
                return

    def _off_blocks_rect(self) -> pygame.Rect:
        return pygame.Rect(60, 165, 200, 26)

    def _off_trees_rect(self) -> pygame.Rect:
        return pygame.Rect(480, 165, 200, 26)

    def _cheats_rect(self) -> pygame.Rect:
        return pygame.Rect(60, 600, 24, 24)

    def _draw(self) -> None:
        if self.background is not None:
            self.screen.blit(self.background, (0, 0))
            overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 12, 20, 220))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(settings.COLOR_BG)

        title = self.font_h1.render("Настройки", True, settings.COLOR_TEXT)
        self.screen.blit(title, (40, 20))

        for b in self.buttons:
            b.draw(self.screen)

        # === Текстуры блоков ===
        self.screen.blit(self.font_h2.render("Текстур-пак блоков", True, settings.COLOR_TEXT), (60, 120))
        
        off_b = self._off_blocks_rect()
        selected = library.get_active() is None
        color = settings.COLOR_ACCENT if selected else settings.COLOR_BUTTON
        pygame.draw.rect(self.screen, color, off_b, border_radius=4)
        lbl = self.font_small.render("Процедурные", True, settings.COLOR_TEXT)
        self.screen.blit(lbl, lbl.get_rect(center=off_b.center))

        for i, rect in enumerate(self.block_rows):
            name = self.block_sets[i]
            is_active = (name == library.get_active())
            bg = settings.COLOR_ACCENT_DARK if is_active else settings.COLOR_PANEL
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, settings.COLOR_PANEL_BORDER, rect, 2, border_radius=4)
            marker = "● " if is_active else "  "
            c = settings.COLOR_ACCENT if is_active else settings.COLOR_TEXT
            s = self.font_small.render(marker + name, True, c)
            self.screen.blit(s, (rect.x + 8, rect.y + 4))

        # === Текстуры деревьев ===
        self.screen.blit(self.font_h2.render("Текстур-пак деревьев", True, settings.COLOR_TEXT), (480, 120))
        
        off_t = self._off_trees_rect()
        from scripts.texture_gen import tree_library
        selected = tree_library.get_active() is None
        color = settings.COLOR_ACCENT if selected else settings.COLOR_BUTTON
        pygame.draw.rect(self.screen, color, off_t, border_radius=4)
        lbl = self.font_small.render("Стандартные", True, settings.COLOR_TEXT)
        self.screen.blit(lbl, lbl.get_rect(center=off_t.center))

        for i, rect in enumerate(self.tree_rows):
            name = self.tree_sets[i]
            is_active = (name == tree_library.get_active())
            bg = settings.COLOR_ACCENT_DARK if is_active else settings.COLOR_PANEL
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, settings.COLOR_PANEL_BORDER, rect, 2, border_radius=4)
            marker = "● " if is_active else "  "
            c = settings.COLOR_ACCENT if is_active else settings.COLOR_TEXT
            s = self.font_small.render(marker + name, True, c)
            self.screen.blit(s, (rect.x + 8, rect.y + 4))

        # === Читы ===
        self.screen.blit(self.font_h2.render("Читы", True, settings.COLOR_TEXT), (60, 560))
        cb = self._cheats_rect()
        pygame.draw.rect(self.screen, settings.COLOR_PANEL, cb, border_radius=3)
        pygame.draw.rect(self.screen, settings.COLOR_PANEL_BORDER, cb, 2, border_radius=3)
        if self.cheats:
            pygame.draw.line(self.screen, settings.COLOR_ACCENT, (cb.x + 4, cb.centery), (cb.centerx, cb.bottom - 5), 3)
            pygame.draw.line(self.screen, settings.COLOR_ACCENT, (cb.centerx, cb.bottom - 5), (cb.right - 4, cb.y + 4), 3)
        ch_lbl = self.font_med.render("Разрешить промотку времени (T)", True, settings.COLOR_TEXT)
        self.screen.blit(ch_lbl, (cb.right + 10, cb.y + 1))

        # Тост
        if self.toast_timer > 0:
            s = self.font_med.render(self.toast, True, settings.COLOR_TEXT)
            pad = 12
            r = s.get_rect()
            r.inflate_ip(pad * 2, pad)
            r.midbottom = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT - 140)
            pygame.draw.rect(self.screen, settings.COLOR_PANEL, r, border_radius=6)
            pygame.draw.rect(self.screen, settings.COLOR_ACCENT, r, 2, border_radius=6)
            self.screen.blit(s, s.get_rect(center=r.center))

# ---------------------------------------------------------------------------
# Меню генератора (подменю)
# ---------------------------------------------------------------------------

class GeneratorMenu:
    """Список генераторов. Открывается и из паузы, и из главного меню."""

    def __init__(self, screen: pygame.Surface,
                 background: pygame.Surface | None = None):
        self.screen = screen
        self.background = background
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_h1 = settings.get_font(28, bold=True)
        self.font_med = settings.get_font(18)
        self.font_small = settings.get_font(15)

        w, h = 400, 50
        cx = settings.SCREEN_WIDTH // 2
        y0 = 200
        gap = 58

        self.buttons = [
            _Button((cx - w // 2, y0,               w, h),
                    "Текстуры блоков", self._open_textures, self.font_med),
            _Button((cx - w // 2, y0 + gap,         w, h),
                    "Растительность",  self._open_flora, self.font_med),
            _Button((cx - w // 2, y0 + gap * 2,     w, h),
                    "Животные (скоро)",  lambda: None, self.font_med,
                    enabled=False),
            _Button((cx - w // 2, y0 + gap * 3,     w, h),
                    "Инструменты (скоро)", lambda: None, self.font_med,
                    enabled=False),
            _Button((cx - w // 2, y0 + gap * 4,     w, h),
                    "Броня (скоро)",     lambda: None, self.font_med,
                    enabled=False),
            _Button((cx - w // 2, y0 + gap * 5 + 20, w, h),
                    "← Назад", self._close, self.font_med),
        ]

    def _open_textures(self):
        from scripts.game_logic.texture_editor import TextureEditor
        TextureEditor(self.screen).run()

    def _open_flora(self):
        FloraMenu(self.screen).run()

    def _close(self):
        self.running = False

    def run(self):
        while self.running:
            self.clock.tick(settings.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.event.post(event)
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    for b in self.buttons:
                        b.handle(event)
            self._draw()
            pygame.display.flip()

    def _draw(self):
        if self.background is not None:
            self.screen.blit(self.background, (0, 0))
            ov = pygame.Surface(
                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
                pygame.SRCALPHA)
            ov.fill((10, 12, 20, 210))
            self.screen.blit(ov, (0, 0))
        else:
            self.screen.fill(settings.COLOR_BG)

        t = self.font_h1.render("Генератор", True, settings.COLOR_TEXT)
        self.screen.blit(t, t.get_rect(
            center=(settings.SCREEN_WIDTH // 2, 130)))

        sub = self.font_small.render(
            "Выберите раздел процедурной генерации",
            True, settings.COLOR_TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(
            center=(settings.SCREEN_WIDTH // 2, 165)))

        for b in self.buttons:
            b.draw(self.screen)


# ---------------------------------------------------------------------------
# Подменю растительности
# ---------------------------------------------------------------------------
class FloraMenu:
    """Деревья / кусты / трава-цветы."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_h1 = settings.get_font(28, bold=True)
        self.font_med = settings.get_font(18)
        self.font_small = settings.get_font(15)

        w, h = 400, 50
        cx = settings.SCREEN_WIDTH // 2
        self.buttons = [
            _Button((cx - w // 2, 240, w, h),
                    "Деревья", self._open_trees, self.font_med),
            _Button((cx - w // 2, 306, w, h),
                    "Кусты (скоро)", lambda: None, self.font_med,
                    enabled=False),
            _Button((cx - w // 2, 372, w, h),
                    "Трава и цветы (скоро)", lambda: None, self.font_med,
                    enabled=False),
            _Button((cx - w // 2, 470, w, h),
                    "← Назад", self._close, self.font_med),
        ]

    def _open_trees(self):
        from scripts.game_logic.tree_editor import TreeEditor
        TreeEditor(self.screen).run()

    def _close(self):
        self.running = False

    def run(self):
        while self.running:
            self.clock.tick(settings.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.event.post(event)
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    for b in self.buttons:
                        b.handle(event)
            self._draw()
            pygame.display.flip()

    def _draw(self):
        self.screen.fill(settings.COLOR_BG)
        t = self.font_h1.render("Растительность", True, settings.COLOR_TEXT)
        self.screen.blit(t, t.get_rect(
            center=(settings.SCREEN_WIDTH // 2, 150)))
        for b in self.buttons:
            b.draw(self.screen)


# ---------------------------------------------------------------------------
# Меню паузы
# ---------------------------------------------------------------------------

class PauseMenu:
    """Блокирующий цикл. Возвращает 'continue' | 'menu' | 'quit'."""

    def __init__(self, screen: pygame.Surface, game):
        self.screen = screen
        self.game = game
        self.clock = pygame.time.Clock()
        self.running = True
        self.result = "continue"

        # Снимок текущего кадра — фон для паузы
        self.background = screen.copy()

        self.font_h1 = settings.get_font(36, bold=True)
        self.font_med = settings.get_font(20)
        self.font_small = settings.get_font(14)

        w, h = 360, 50
        cx = settings.SCREEN_WIDTH // 2
        y = 200
        gap = 60

        self.buttons = [
            _Button((cx - w // 2, y,               w, h),
                    "Продолжить", self._continue, self.font_med),
            _Button((cx - w // 2, y + gap,         w, h),
                    "Сохранить",  self._save,     self.font_med),
            _Button((cx - w // 2, y + gap * 2,     w, h),
                    "Настройки",  self._settings, self.font_med),
            _Button((cx - w // 2, y + gap * 3,     w, h),
                    "Генератор",  self._generator, self.font_med),
            _Button((cx - w // 2, y + gap * 4,     w, h),
                    "В главное меню", self._to_main_menu, self.font_med,
                    danger=True),
            _Button((cx - w // 2, y + gap * 5,     w, h),
                    "Выход из игры", self._quit, self.font_med, danger=True),
        ]

        self.toast = ""
        self.toast_timer = 0.0

    def _continue(self):
        self.result = "continue"
        self.running = False

    def _save(self):
        self.game.world.save()
        self._toast("Мир сохранён")

    def _settings(self):
        SettingsScreen(self.screen, self.game, self.background).run()
        self.background = self.screen.copy()

    def _generator(self):
        GeneratorMenu(self.screen, self.background).run()
        self.background = self.screen.copy()

    def _to_main_menu(self):
        self.result = "menu"
        self.running = False

    def _quit(self):
        self.result = "quit"
        self.running = False

    def _toast(self, text: str) -> None:
        self.toast = text
        self.toast_timer = 2.0

    def run(self) -> str:
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.result = "quit"
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._continue()
                else:
                    for b in self.buttons:
                        b.handle(event)

            if self.toast_timer > 0:
                self.toast_timer -= dt

            self._draw()
            pygame.display.flip()

        return self.result

    def _draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        ov = pygame.Surface(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((8, 10, 18, 190))
        self.screen.blit(ov, (0, 0))

        t = self.font_h1.render("Пауза", True, settings.COLOR_TEXT)
        self.screen.blit(t, t.get_rect(
            center=(settings.SCREEN_WIDTH // 2, 130)))

        for b in self.buttons:
            b.draw(self.screen)

        if self.toast_timer > 0:
            s = self.font_med.render(self.toast, True, settings.COLOR_TEXT)
            pad = 12
            r = s.get_rect()
            r.inflate_ip(pad * 2, pad)
            r.midbottom = (settings.SCREEN_WIDTH // 2,
                           settings.SCREEN_HEIGHT - 30)
            pygame.draw.rect(self.screen, settings.COLOR_PANEL, r,
                             border_radius=6)
            pygame.draw.rect(self.screen, settings.COLOR_ACCENT, r, 2,
                             border_radius=6)
            self.screen.blit(s, s.get_rect(center=r.center))
            
            