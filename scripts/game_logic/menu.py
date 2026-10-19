# scripts/game_logic/menu.py
from __future__ import annotations

import random
from datetime import datetime

import pygame

from scripts.config import settings
from scripts.utils import file_utils
from scripts.utils.math_utils import random_seed


# ---------------------------------------------------------------------------
# Кнопка
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, rect, text, callback=None, font=None,
                 color=None, hover_color=None, danger=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font = font
        self.base_color = color or (settings.COLOR_DANGER if danger
                                    else settings.COLOR_BUTTON)
        self.hover_color = hover_color or (settings.COLOR_DANGER_HOVER if danger
                                           else settings.COLOR_BUTTON_HOVER)
        self.hovered = False
        self.enabled = True

    def handle_event(self, event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.callback:
                self.callback()
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        color = self.hover_color if self.hovered else self.base_color
        if not self.enabled:
            color = tuple(c // 2 for c in color)

        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, settings.COLOR_BORDER, self.rect, 2,
                         border_radius=4)
        if self.font:
            txt = self.font.render(self.text, True, settings.COLOR_TEXT)
            surface.blit(txt, txt.get_rect(center=self.rect.center))


# ---------------------------------------------------------------------------
# Меню
# ---------------------------------------------------------------------------
class Menu:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "main"
        self.result: str | None = None

        # Шрифты
        self.font_title = settings.get_font(64, bold=True)
        self.font_h1    = settings.get_font(36, bold=True)
        self.font_h2    = settings.get_font(26, bold=True)
        self.font_med   = settings.get_font(20)
        self.font_small = settings.get_font(16)
        self.font_tiny  = settings.get_font(13)

        # Звёзды на фоне
        rng = random.Random(1337)
        self.stars = [
            (rng.randint(0, settings.SCREEN_WIDTH),
             rng.randint(0, settings.SCREEN_HEIGHT),
             rng.choice([1, 1, 1, 2]))
            for _ in range(140)
        ]
        self.star_time = 0.0

        # Список сохранений
        self.save_list: list[dict] = []
        self.save_hover_idx = -1
        self.save_delete_mode = False
        self.pending_delete: str | None = None

        # Данные «нового мира»
        self.input_name = ""
        self.input_seed = ""
        self.active_input = "name"
        self.selected_size = "medium"
        self.selected_noise = "value"      # "value" | "opensimplex"

        # Тост
        self.toast = ""
        self.toast_timer = 0.0

        self._build_main_buttons()

    # ------------------------------------------------------------------
    # Главное меню
    # ------------------------------------------------------------------
    def _build_main_buttons(self) -> None:
        cx = settings.SCREEN_WIDTH // 2
        w, h = 340, 52
        y0 = 260
        gap = 60

        self.main_buttons = [
            Button((cx - w // 2, y0,               w, h),
                   "Новая игра",  self._go_new_world,  self.font_med),
            Button((cx - w // 2, y0 + gap,         w, h),
                   "Продолжить",  self._go_save_select, self.font_med),
            Button((cx - w // 2, y0 + gap * 2,     w, h),
                   "Генератор", self._go_texture_editor, self.font_med),
            Button((cx - w // 2, y0 + gap * 3,     w, h),
                   "Настройки",   self._go_settings,  self.font_med),
            Button((cx - w // 2, y0 + gap * 4,     w, h),
                   "Выход",       self._quit,         self.font_med, danger=True),
        ]

    # ------------------------------------------------------------------
    # Колбэки главного меню
    # ------------------------------------------------------------------
    def _go_new_world(self) -> None:
        self.input_name = ""
        self.input_seed = ""
        self.active_input = "name"
        self.selected_size = "medium"
        self.selected_noise = "value"
        self.state = "new_world"

    def _go_save_select(self) -> None:
        self.save_list = file_utils.list_saves()
        self.save_hover_idx = -1
        self.pending_delete = None
        self.save_delete_mode = False
        self.state = "save_select"

    def _go_texture_editor(self) -> None:
        from scripts.game_logic.pause_menu import GeneratorMenu
        GeneratorMenu(self.screen).run()
        self.state = "main"

    def _go_settings(self) -> None:
        self.state = "settings"

    def _quit(self) -> None:
        self.result = None
        self.running = False

    # ------------------------------------------------------------------
    # Главный цикл
    # ------------------------------------------------------------------
    def run(self) -> str | None:
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            self.star_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.result = None
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._on_escape()
                else:
                    self._handle_state_event(event)

            if self.toast_timer > 0:
                self.toast_timer -= dt

            self._draw()
            pygame.display.flip()

        return self.result

    def _on_escape(self) -> None:
        if self.state == "main":
            self._quit()
        elif self.state in ("save_select", "new_world", "settings"):
            if self.pending_delete:
                self.pending_delete = None
            else:
                self.state = "main"

    def _handle_state_event(self, event) -> None:
        if self.state == "main":
            for b in self.main_buttons:
                b.handle_event(event)
        elif self.state == "save_select":
            self._handle_save_select(event)
        elif self.state == "new_world":
            self._handle_new_world(event)
        elif self.state == "settings":
            self._handle_settings(event)

    # ------------------------------------------------------------------
    # Экран: список сохранений
    # ------------------------------------------------------------------
    def _handle_save_select(self, event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.save_hover_idx = self._save_hit_test(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self._save_hit_test(event.pos)
            if idx >= 0:
                save = self.save_list[idx]
                if self.pending_delete == save["folder"]:
                    file_utils.delete_save(save["folder"])
                    self._show_toast("Сохранение удалено")
                    self.save_list = file_utils.list_saves()
                    self.pending_delete = None
                elif self.save_delete_mode:
                    self.pending_delete = save["folder"]
                else:
                    file_utils.update_last_played(save["folder"])
                    self.result = save["folder"]
                    self.running = False

            if self._back_button_rect().collidepoint(event.pos):
                self.state = "main"
                self.pending_delete = None
            if self._delete_toggle_rect().collidepoint(event.pos):
                self.save_delete_mode = not self.save_delete_mode
                self.pending_delete = None

    def _save_hit_test(self, pos) -> int:
        x, y = pos
        list_top = 200
        row_h = 84
        for i in range(len(self.save_list)):
            r = pygame.Rect(240, list_top + i * row_h, 800, row_h - 12)
            if r.collidepoint(x, y):
                return i
        return -1

    def _back_button_rect(self) -> pygame.Rect:
        return pygame.Rect(40, settings.SCREEN_HEIGHT - 80, 160, 48)

    def _delete_toggle_rect(self) -> pygame.Rect:
        return pygame.Rect(settings.SCREEN_WIDTH - 240,
                           settings.SCREEN_HEIGHT - 80, 200, 48)

    def _draw_save_select(self) -> None:
        self._blit_center(self.font_h1, "Выбор сохранения",
                          settings.SCREEN_WIDTH // 2, 100)

        if not self.save_list:
            msg = self.font_med.render(
                "Нет сохранений. Создайте новую игру в главном меню.",
                True, settings.COLOR_TEXT_DIM)
            self.screen.blit(msg, msg.get_rect(
                center=(settings.SCREEN_WIDTH // 2, 340)))

        list_top = 200
        row_h = 84
        for i, save in enumerate(self.save_list):
            rect = pygame.Rect(240, list_top + i * row_h, 800, row_h - 12)
            hovered = (i == self.save_hover_idx)

            bg = settings.COLOR_BUTTON_HOVER if hovered else settings.COLOR_PANEL
            if self.pending_delete == save["folder"]:
                bg = settings.COLOR_DANGER
            pygame.draw.rect(self.screen, bg, rect, border_radius=6)
            pygame.draw.rect(self.screen, settings.COLOR_PANEL_BORDER,
                             rect, 2, border_radius=6)

            name_surf = self.font_h2.render(save.get("name", "?"),
                                            True, settings.COLOR_TEXT)
            self.screen.blit(name_surf, (rect.x + 20, rect.y + 12))

            size_label = {"small": "малый",
                          "medium": "средний",
                          "large": "большой"}.get(save.get("size"), "?")
            noise_label = save.get("noise_kind", "value")
            sub = (f"Размер: {size_label}   "
                   f"Шум: {noise_label}   "
                   f"Сид: {save.get('seed')}   "
                   f"Играно: {self._fmt_date(save.get('last_played'))}")
            sub_surf = self.font_small.render(sub, True, settings.COLOR_TEXT_DIM)
            self.screen.blit(sub_surf, (rect.x + 20, rect.y + 44))

            if self.pending_delete == save["folder"]:
                warn = self.font_small.render(
                    "Нажмите ещё раз, чтобы удалить", True, (255, 220, 220))
                self.screen.blit(warn, (rect.right - warn.get_width() - 20,
                                        rect.y + 48))

        back = self._back_button_rect()
        pygame.draw.rect(self.screen, settings.COLOR_BUTTON, back,
                         border_radius=4)
        pygame.draw.rect(self.screen, settings.COLOR_BORDER, back, 2,
                         border_radius=4)
        bt = self.font_med.render("Назад", True, settings.COLOR_TEXT)
        self.screen.blit(bt, bt.get_rect(center=back.center))

        toggle = self._delete_toggle_rect()
        color = (settings.COLOR_DANGER if self.save_delete_mode
                 else settings.COLOR_BUTTON)
        pygame.draw.rect(self.screen, color, toggle, border_radius=4)
        pygame.draw.rect(self.screen, settings.COLOR_BORDER, toggle, 2,
                         border_radius=4)
        label = ("Режим удаления: ВКЛ" if self.save_delete_mode
                 else "Режим удаления: выкл")
        tt = self.font_small.render(label, True, settings.COLOR_TEXT)
        self.screen.blit(tt, tt.get_rect(center=toggle.center))

    # ------------------------------------------------------------------
    # Экран: создание нового мира
    # ------------------------------------------------------------------
    def _handle_new_world(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._name_rect().collidepoint(event.pos):
                self.active_input = "name"
            elif self._seed_rect().collidepoint(event.pos):
                self.active_input = "seed"

            for key, rect in self._size_rects().items():
                if rect.collidepoint(event.pos):
                    self.selected_size = key

            for key, rect in self._noise_rects().items():
                if rect.collidepoint(event.pos):
                    self.selected_noise = key

            if self._create_rect().collidepoint(event.pos):
                self._do_create_world()
            elif self._cancel_rect().collidepoint(event.pos):
                self.state = "main"

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._do_create_world()
                return

            target = (self.input_name if self.active_input == "name"
                      else self.input_seed)
            if event.key == pygame.K_TAB:
                self.active_input = ("seed" if self.active_input == "name"
                                     else "name")
            elif event.key == pygame.K_BACKSPACE:
                target = target[:-1]
            elif event.unicode and event.unicode.isprintable():
                if self.active_input == "name":
                    if len(target) < 24:
                        target += event.unicode
                else:
                    if event.unicode.isdigit() and len(target) < 12:
                        target += event.unicode

            if self.active_input == "name":
                self.input_name = target
            else:
                self.input_seed = target

    def _name_rect(self) -> pygame.Rect:
        return pygame.Rect(settings.SCREEN_WIDTH // 2 - 250, 220, 500, 48)

    def _seed_rect(self) -> pygame.Rect:
        return pygame.Rect(settings.SCREEN_WIDTH // 2 - 250, 320, 500, 48)

    def _size_rects(self) -> dict[str, pygame.Rect]:
        cx = settings.SCREEN_WIDTH // 2
        y = 415
        w, h = 160, 56
        gap = 24
        rects = {}
        keys = ["small", "medium", "large"]
        total = len(keys) * w + (len(keys) - 1) * gap
        x0 = cx - total // 2
        for i, key in enumerate(keys):
            rects[key] = pygame.Rect(x0 + i * (w + gap), y, w, h)
        return rects

    def _noise_rects(self) -> dict[str, pygame.Rect]:
        cx = settings.SCREEN_WIDTH // 2
        y = 540
        w, h = 200, 44
        return {
            "value":       pygame.Rect(cx - 210, y, w, h),
            "opensimplex": pygame.Rect(cx + 10, y, w, h),
        }

    def _create_rect(self) -> pygame.Rect:
        cx = settings.SCREEN_WIDTH // 2
        return pygame.Rect(cx - 220, 620, 200, 56)

    def _cancel_rect(self) -> pygame.Rect:
        cx = settings.SCREEN_WIDTH // 2
        return pygame.Rect(cx + 20, 620, 200, 56)

    def _do_create_world(self) -> None:
        name = self.input_name.strip() or "Новый мир"
        if self.input_seed.strip():
            seed = int(self.input_seed)
        else:
            seed = random_seed()

        folder, _meta = file_utils.create_save(
            name, seed, self.selected_size,
            noise_kind=self.selected_noise)
        self._show_toast(f"Мир создан: {name} (сид {seed})")
        self.result = folder
        self._draw()
        pygame.display.flip()
        pygame.time.wait(400)
        self.running = False

    def _draw_new_world(self) -> None:
        self._blit_center(self.font_h1, "Создание нового мира",
                          settings.SCREEN_WIDTH // 2, 100)

        # Поля ввода
        self._draw_labeled_input(
            self._name_rect(), "Название мира (Tab — переключить поле)",
            self.input_name, self.active_input == "name")
        self._draw_labeled_input(
            self._seed_rect(), "Сид (пусто = случайный)",
            self.input_seed, self.active_input == "seed")

        # Размер мира
        self._blit_center(self.font_med, "Размер мира",
                          settings.SCREEN_WIDTH // 2, 390)
        labels = {"small": "Малый", "medium": "Средний", "large": "Большой"}
        sizes = settings.WORLD_SIZES
        for key, rect in self._size_rects().items():
            selected = (key == self.selected_size)
            color = settings.COLOR_ACCENT if selected else settings.COLOR_BUTTON
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, settings.COLOR_BORDER, rect, 2,
                             border_radius=4)
            txt = self.font_med.render(labels[key], True, settings.COLOR_TEXT)
            self.screen.blit(txt, txt.get_rect(center=rect.center))

            w, h = sizes[key]
            sub = self.font_tiny.render(f"{w}×{h}", True,
                                        settings.COLOR_TEXT_DIM)
            self.screen.blit(sub, sub.get_rect(
                center=(rect.centerx, rect.bottom + 14)))

        # Тип шума
        self._blit_center(self.font_med, "Тип шума для рельефа",
                          settings.SCREEN_WIDTH // 2, 512)
        noise_labels = {"value": "Value noise",
                        "opensimplex": "OpenSimplex"}
        for key, rect in self._noise_rects().items():
            selected = (key == self.selected_noise)
            color = settings.COLOR_ACCENT if selected else settings.COLOR_BUTTON
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, settings.COLOR_BORDER, rect, 2,
                             border_radius=4)
            txt = self.font_med.render(noise_labels[key], True,
                                       settings.COLOR_TEXT)
            self.screen.blit(txt, txt.get_rect(center=rect.center))

        # Кнопки
        create = self._create_rect()
        pygame.draw.rect(self.screen, settings.COLOR_ACCENT, create,
                         border_radius=4)
        pygame.draw.rect(self.screen, settings.COLOR_BORDER, create, 2,
                         border_radius=4)
        ct = self.font_med.render("Создать и играть", True,
                                  settings.COLOR_BG_DARK)
        self.screen.blit(ct, ct.get_rect(center=create.center))

        cancel = self._cancel_rect()
        pygame.draw.rect(self.screen, settings.COLOR_BUTTON, cancel,
                         border_radius=4)
        pygame.draw.rect(self.screen, settings.COLOR_BORDER, cancel, 2,
                         border_radius=4)
        xt = self.font_med.render("Отмена", True, settings.COLOR_TEXT)
        self.screen.blit(xt, xt.get_rect(center=cancel.center))

    def _draw_labeled_input(self, rect, label, value, active) -> None:
        lbl = self.font_small.render(label, True, settings.COLOR_TEXT_DIM)
        self.screen.blit(lbl, (rect.x, rect.y - 22))

        pygame.draw.rect(self.screen, settings.COLOR_PANEL, rect,
                         border_radius=4)
        border = settings.COLOR_ACCENT if active else settings.COLOR_PANEL_BORDER
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=4)

        text = value
        if active and int(self.star_time * 2) % 2 == 0:
            text += "|"
        surf = self.font_med.render(text, True, settings.COLOR_TEXT_INPUT)
        self.screen.blit(surf, (rect.x + 12,
                                rect.centery - surf.get_height() // 2))

    # ------------------------------------------------------------------
    # Экран: настройки
    # ------------------------------------------------------------------
    def _handle_settings(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._settings_back_rect().collidepoint(event.pos):
                self.state = "main"

    def _settings_back_rect(self) -> pygame.Rect:
        return pygame.Rect(40, settings.SCREEN_HEIGHT - 80, 160, 48)

    def _draw_settings(self) -> None:
        self._blit_center(self.font_h1, "Настройки",
                          settings.SCREEN_WIDTH // 2, 100)
        self._blit_center(self.font_med,
                          "Полные настройки доступны в игре через ESC.",
                          settings.SCREEN_WIDTH // 2, 300)
        self._blit_center(self.font_small,
                          "(текстур-пак, читы, громкость и т. д.)",
                          settings.SCREEN_WIDTH // 2, 340,
                          color=settings.COLOR_TEXT_DIM)

        back = self._settings_back_rect()
        pygame.draw.rect(self.screen, settings.COLOR_BUTTON, back,
                         border_radius=4)
        pygame.draw.rect(self.screen, settings.COLOR_BORDER, back, 2,
                         border_radius=4)
        bt = self.font_med.render("Назад", True, settings.COLOR_TEXT)
        self.screen.blit(bt, bt.get_rect(center=back.center))

    # ------------------------------------------------------------------
    # Фон и утилиты
    # ------------------------------------------------------------------
    def _draw_background(self) -> None:
        self.screen.fill(settings.COLOR_BG)
        for i in range(0, settings.SCREEN_HEIGHT, 4):
            t = i / settings.SCREEN_HEIGHT
            color = (
                int(settings.COLOR_BG_DARK[0] * (1 - t) + settings.COLOR_BG[0] * t),
                int(settings.COLOR_BG_DARK[1] * (1 - t) + settings.COLOR_BG[1] * t),
                int(settings.COLOR_BG_DARK[2] * (1 - t) + settings.COLOR_BG[2] * t),
            )
            pygame.draw.rect(self.screen, color,
                             (0, i, settings.SCREEN_WIDTH, 4))

        for x, y, size in self.stars:
            phase = (self.star_time + x * 0.013 + y * 0.007) % 3.0
            alpha = 120 + int(100 * (phase / 3.0))
            col = settings.COLOR_STAR
            r = size if alpha > 180 else max(1, size - 1)
            pygame.draw.rect(self.screen, col, (x, y, r, r))

    def _blit_center(self, font, text, cx, cy, color=None) -> None:
        surf = font.render(text, True, color or settings.COLOR_TEXT)
        self.screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def _show_toast(self, text: str) -> None:
        self.toast = text
        self.toast_timer = 2.0

    def _draw_toast(self) -> None:
        if self.toast_timer <= 0:
            return
        surf = self.font_med.render(self.toast, True, settings.COLOR_TEXT)
        pad = 14
        rect = surf.get_rect()
        rect.inflate_ip(pad * 2, pad)
        rect.midbottom = (settings.SCREEN_WIDTH // 2,
                          settings.SCREEN_HEIGHT - 24)
        pygame.draw.rect(self.screen, settings.COLOR_PANEL, rect,
                         border_radius=6)
        pygame.draw.rect(self.screen, settings.COLOR_ACCENT, rect, 2,
                         border_radius=6)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _fmt_date(self, iso: str | None) -> str:
        if not iso:
            return "—"
        try:
            dt = datetime.fromisoformat(iso)
            return dt.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return iso

    # ------------------------------------------------------------------
    # Мастер-отрисовка
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        self._draw_background()

        if self.state == "main":
            self._blit_center(self.font_title, "TERRARIA-LIKE",
                              settings.SCREEN_WIDTH // 2, 150,
                              color=settings.COLOR_ACCENT)
            self._blit_center(self.font_small, "v0.1 — прототип",
                              settings.SCREEN_WIDTH // 2, 195,
                              color=settings.COLOR_TEXT_DIM)
            for b in self.main_buttons:
                b.draw(self.screen)

        elif self.state == "save_select":
            self._draw_save_select()

        elif self.state == "new_world":
            self._draw_new_world()

        elif self.state == "settings":
            self._draw_settings()

        self._draw_toast()
        