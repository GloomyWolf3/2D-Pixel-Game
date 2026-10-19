# scripts/game_logic/texture_editor.py
"""Экран «Генератор текстур блоков» в духе MCreate."""
from __future__ import annotations

import colorsys
import random

import pygame

from scripts.config import settings
from scripts.game_logic import tiles as T
from scripts.texture_gen import library
from scripts.texture_gen.generator import generate_surface
from scripts.texture_gen.params import TextureParams


# ---------------------------------------------------------------------------
# Виджеты
# ---------------------------------------------------------------------------

class Slider:
    def __init__(self, x, y, w, label, min_v, max_v, value,
                 fmt="{:.2f}", step=None):
        self.rect = pygame.Rect(x, y, w, 8)
        self.hit_rect = pygame.Rect(x - 8, y - 14, w + 16, 30)
        self.label = label
        self.min_v = min_v
        self.max_v = max_v
        self.value = float(value)
        self.fmt = fmt
        self.step = step
        self.dragging = False

    def _to_x(self, v):
        t = (v - self.min_v) / (self.max_v - self.min_v)
        return self.rect.x + int(t * self.rect.w)

    def _from_x(self, x):
        t = (x - self.rect.x) / max(1, self.rect.w)
        t = max(0.0, min(1.0, t))
        v = self.min_v + t * (self.max_v - self.min_v)
        if self.step:
            v = round(v / self.step) * self.step
        return v

    def handle(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hit_rect.collidepoint(event.pos):
                self.dragging = True
                nv = self._from_x(event.pos[0])
                changed = abs(nv - self.value) > 1e-6
                self.value = nv
                return changed
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            nv = self._from_x(event.pos[0])
            changed = abs(nv - self.value) > 1e-6
            self.value = nv
            return changed
        return False

    def draw(self, surface, font):
        s = font.render(f"{self.label}: {self.fmt.format(self.value)}",
                        True, (220, 220, 220))
        surface.blit(s, (self.rect.x, self.rect.y - 18))
        pygame.draw.rect(surface, (60, 64, 80), self.rect, border_radius=3)
        t = (self.value - self.min_v) / (self.max_v - self.min_v)
        fill = pygame.Rect(self.rect.x, self.rect.y,
                           int(t * self.rect.w), self.rect.h)
        pygame.draw.rect(surface, (140, 210, 130), fill, border_radius=3)
        kx = self._to_x(self.value)
        pygame.draw.circle(surface, (240, 240, 240),
                           (kx, self.rect.centery), 6)
        pygame.draw.circle(surface, (40, 44, 56),
                           (kx, self.rect.centery), 6, 2)


class Checkbox:
    def __init__(self, x, y, label, value):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.label = label
        self.value = value

    def handle(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # клик по чекбоксу или по подписи
            hit = self.rect.inflate(140, 6)
            if hit.collidepoint(event.pos):
                self.value = not self.value
                return True
        return False

    def draw(self, surface, font):
        pygame.draw.rect(surface, (40, 44, 56), self.rect, border_radius=3)
        pygame.draw.rect(surface, (110, 118, 140), self.rect, 2, border_radius=3)
        if self.value:
            pygame.draw.line(surface, (180, 240, 160),
                             (self.rect.x + 4, self.rect.centery),
                             (self.rect.centerx, self.rect.bottom - 5), 3)
            pygame.draw.line(surface, (180, 240, 160),
                             (self.rect.centerx, self.rect.bottom - 5),
                             (self.rect.right - 4, self.rect.y + 4), 3)
        s = font.render(self.label, True, (220, 220, 220))
        surface.blit(s, (self.rect.right + 8, self.rect.y + 2))


class ColorPicker:
    """Плашка текущего цвета + всплывающая палитра 8×4."""
    CELL = 20
    COLS = 8
    ROWS = 4

    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, 30, 22)
        self.color = tuple(color)
        self.open = False
        self.palette = self._build_palette()

    @staticmethod
    def _build_palette() -> list[tuple[int, int, int]]:
        colors = []
        for row in range(3):
            s = 1.0 - row * 0.30
            v = 1.0 - row * 0.15
            for col in range(8):
                h = col / 8.0
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                colors.append((int(r * 255), int(g * 255), int(b * 255)))
        for g in (15, 60, 110, 160, 200, 240, 255, 0):
            colors.append((g, g, g))
        return colors

    def panel_rect(self) -> pygame.Rect:
        w = self.COLS * self.CELL
        h = self.ROWS * self.CELL
        return pygame.Rect(self.rect.x, self.rect.y + self.rect.h + 4, w, h)

    def handle(self, event) -> bool:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        if self.open:
            pr = self.panel_rect()
            if pr.collidepoint(event.pos):
                col = (event.pos[0] - pr.x) // self.CELL
                row = (event.pos[1] - pr.y) // self.CELL
                idx = row * self.COLS + col
                if 0 <= idx < len(self.palette):
                    self.color = self.palette[idx]
                    self.open = False
                    return True
                return False
            else:
                self.open = False
                return False

        if self.rect.collidepoint(event.pos):
            self.open = True
            return False
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=3)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2, border_radius=3)

    def draw_panel(self, surface):
        if not self.open:
            return
        pr = self.panel_rect()
        pygame.draw.rect(surface, (20, 22, 30), pr, border_radius=4)
        pygame.draw.rect(surface, (110, 118, 140), pr, 2, border_radius=4)
        for idx, c in enumerate(self.palette):
            row = idx // self.COLS
            col = idx % self.COLS
            x = pr.x + col * self.CELL
            y = pr.y + row * self.CELL
            pygame.draw.rect(surface, c,
                             (x + 2, y + 2, self.CELL - 4, self.CELL - 4))


# ---------------------------------------------------------------------------
# Экран редактора
# ---------------------------------------------------------------------------

class TextureEditor:
    TOP = 56
    LEFT_W = 360

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True

        # Данные редактирования
        self.tile_params: dict[int, TextureParams] = {
            tid: p.copy() for tid, p in library.PRESETS.items()
        }
        self.current_tile = T.DIRT

        # Раскрытая секция узоров: None / "veins" / "cracks" / "speckles"
        self.pattern_section: str | None = None

        # Шрифты
        self.font_h1 = settings.get_font(24, bold=True)
        self.font_h2 = settings.get_font(18, bold=True)
        self.font_med = settings.get_font(16)
        self.font_small = settings.get_font(14)
        self.font_tiny = settings.get_font(12)

        # Библиотека
        self.sets = library.list_sets()
        self.selected_set: str | None = None
        self.input_name = ""
        self.input_active = False

        # Тост
        self.toast = ""
        self.toast_timer = 0.0

        # Кэш превью
        self._preview_surf = None
        self._preview_key = None
        self._variations: list[pygame.Surface] = []

        self._build_widgets()
        self._refresh_preview()

    # ------------------------------------------------------------------
    # Виджеты
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        p = self.tile_params[self.current_tile]

        sx, sw = 24, 300

        self.sliders = {
            "noise_scale":     Slider(sx, 300, sw, "Масштаб шума",
                                      2, 12, p.noise_scale, "{:.0f}", 1),
            "noise_octaves":   Slider(sx, 324, sw, "Октавы",
                                      1, 4, p.noise_octaves, "{:.0f}", 1),
            "noise_intensity": Slider(sx, 348, sw, "Сила шума",
                                      0.0, 1.0, p.noise_intensity),
            "dark_shift":      Slider(sx, 372, sw, "Затемнение",
                                      0.0, 0.7, p.dark_shift),
            "light_shift":     Slider(sx, 396, sw, "Осветление",
                                      0.0, 0.7, p.light_shift),
            "hue_shift":       Slider(sx, 420, sw, "Сдвиг оттенка",
                                      0.0, 0.15, p.hue_shift),
            "sat_shift":       Slider(sx, 444, sw, "Сдвиг насыщенности",
                                      0.0, 0.5, p.sat_shift),
        }

        self.checkboxes = {
            "veins":    Checkbox(sx, 480, "Вены",     p.veins),
            "cracks":   Checkbox(sx, 540, "Трещины",  p.cracks),
            "speckles": Checkbox(sx, 600, "Крапинки", p.speckles),
        }

        self.color_pickers = {
            "vein":     ColorPicker(300, 479, p.vein_color),
            "crack":    ColorPicker(300, 539, p.crack_color),
            "speckle":  ColorPicker(300, 599, p.speckle_color),
        }

        # Слайдеры узоров (переключаются между секциями)
        self.pattern_sliders = {
            "scale":     Slider(sx, 0, sw, "Размер",
                                2, 10, p.vein_scale, "{:.0f}", 1),
            "intensity": Slider(sx, 0, sw, "Толщина / плотность",
                                0.02, 0.6, p.vein_intensity),
        }
        self._layout_pattern_sliders()

    def _layout_pattern_sliders(self) -> None:
        """Переставить слайдеры узоров в зависимости от раскрытой секции."""
        base_y = {
            "veins":    510,
            "cracks":   570,
            "speckles": 630,
        }.get(self.pattern_section)
        if base_y is None:
            return
        self.pattern_sliders["scale"].rect.y = base_y
        self.pattern_sliders["scale"].hit_rect.y = base_y - 14
        self.pattern_sliders["intensity"].rect.y = base_y + 24
        self.pattern_sliders["intensity"].hit_rect.y = base_y + 24 - 14

    # ------------------------------------------------------------------
    # Синхронизация
    # ------------------------------------------------------------------
    def _sync_params_from_widgets(self) -> None:
        p = self.tile_params[self.current_tile]
        p.noise_scale = int(self.sliders["noise_scale"].value)
        p.noise_octaves = int(self.sliders["noise_octaves"].value)
        p.noise_intensity = self.sliders["noise_intensity"].value
        p.dark_shift = self.sliders["dark_shift"].value
        p.light_shift = self.sliders["light_shift"].value
        p.hue_shift = self.sliders["hue_shift"].value
        p.sat_shift = self.sliders["sat_shift"].value
        p.veins = self.checkboxes["veins"].value
        p.cracks = self.checkboxes["cracks"].value
        p.speckles = self.checkboxes["speckles"].value
        p.vein_color = tuple(self.color_pickers["vein"].color)
        p.crack_color = tuple(self.color_pickers["crack"].color)
        p.speckle_color = tuple(self.color_pickers["speckle"].color)

        sec = self.pattern_section
        if sec:
            scale = int(self.pattern_sliders["scale"].value)
            inten = self.pattern_sliders["intensity"].value
            if sec == "veins":
                p.vein_scale = scale
                p.vein_intensity = inten
            elif sec == "cracks":
                p.crack_scale = scale
                p.crack_intensity = inten
            elif sec == "speckles":
                p.speckle_scale = scale
                p.speckle_intensity = inten

    def _load_params_to_widgets(self) -> None:
        p = self.tile_params[self.current_tile]
        self.sliders["noise_scale"].value = float(p.noise_scale)
        self.sliders["noise_octaves"].value = float(p.noise_octaves)
        self.sliders["noise_intensity"].value = p.noise_intensity
        self.sliders["dark_shift"].value = p.dark_shift
        self.sliders["light_shift"].value = p.light_shift
        self.sliders["hue_shift"].value = p.hue_shift
        self.sliders["sat_shift"].value = p.sat_shift
        self.checkboxes["veins"].value = p.veins
        self.checkboxes["cracks"].value = p.cracks
        self.checkboxes["speckles"].value = p.speckles
        self.color_pickers["vein"].color = tuple(p.vein_color)
        self.color_pickers["crack"].color = tuple(p.crack_color)
        self.color_pickers["speckle"].color = tuple(p.speckle_color)
        self._load_pattern_sliders()

    def _load_pattern_sliders(self) -> None:
        p = self.tile_params[self.current_tile]
        sec = self.pattern_section
        if sec == "veins":
            self.pattern_sliders["scale"].value = float(p.vein_scale)
            self.pattern_sliders["intensity"].value = p.vein_intensity
        elif sec == "cracks":
            self.pattern_sliders["scale"].value = float(p.crack_scale)
            self.pattern_sliders["intensity"].value = p.crack_intensity
        elif sec == "speckles":
            self.pattern_sliders["scale"].value = float(p.speckle_scale)
            self.pattern_sliders["intensity"].value = p.speckle_intensity

    # ------------------------------------------------------------------
    # Превью
    # ------------------------------------------------------------------
    def _refresh_preview(self) -> None:
        self._sync_params_from_widgets()
        p = self.tile_params[self.current_tile]

        key = (self.current_tile, p.seed,
               p.noise_kind, p.noise_scale, p.noise_octaves,
               round(p.noise_intensity, 3), round(p.dark_shift, 3),
               round(p.light_shift, 3), round(p.hue_shift, 3),
               round(p.sat_shift, 3),
               p.veins, p.vein_scale, round(p.vein_intensity, 3),
               tuple(p.vein_color),
               p.cracks, p.crack_scale, round(p.crack_intensity, 3),
               tuple(p.crack_color),
               p.speckles, p.speckle_scale, round(p.speckle_intensity, 3),
               tuple(p.speckle_color))

        if key != self._preview_key:
            self._preview_surf = generate_surface(p)
            self._preview_key = key

            self._variations = []
            for i in range(9):
                q = p.copy()
                q.seed = p.seed + i + 1
                self._variations.append(generate_surface(q))

    # ------------------------------------------------------------------
    # Главный цикл
    # ------------------------------------------------------------------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self._handle_event(event)

            if self.toast_timer > 0:
                self.toast_timer -= dt

            self._draw()
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Обработка событий
    # ------------------------------------------------------------------
    def _handle_event(self, event) -> None:
        # Ввод имени
        if self.input_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.input_name = self.input_name[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.input_active = False
                elif event.unicode and event.unicode.isprintable() \
                        and len(self.input_name) < 32:
                    self.input_name += event.unicode
                return

        # Назад
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_rect().collidepoint(event.pos):
                self.running = False
                return

        # Цветовые пикеры — в приоритете (могут перекрывать слайдеры)
        for cp in self.color_pickers.values():
            if cp.handle(event):
                self._refresh_preview()
                return

        changed = False

        # Слайдеры (основные + узоры)
        for s in self.sliders.values():
            if s.handle(event):
                changed = True
        for s in self.pattern_sliders.values():
            if s.handle(event):
                changed = True

        # Чекбоксы
        for key, cb in self.checkboxes.items():
            if cb.handle(event):
                changed = True
                # Логика раскрытия секции
                if key != self.pattern_section:
                    if cb.value:
                        self.pattern_section = key
                    # если чекбокс выключен и это была активная секция
                    # — оставляем раскрытой (пользователь может снова включить)
                else:
                    if not cb.value:
                        self.pattern_section = None
                self._layout_pattern_sliders()
                self._load_pattern_sliders()

        # Клики по кнопкам/селекторам
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_clicks(event.pos):
                changed = True

        if changed:
            self._refresh_preview()

    def _handle_clicks(self, pos) -> bool:
        changed = False

        # Смена текущего блока
        for tid, rect in self._tile_button_rects().items():
            if rect.collidepoint(pos):
                self.current_tile = tid
                self.pattern_section = None
                self._load_params_to_widgets()
                return True

        # Размер
        for size, rect in self._size_button_rects().items():
            if rect.collidepoint(pos):
                p = self.tile_params[self.current_tile]
                if p.size != size:
                    p.size = size
                    changed = True

        # Вид шума
        for kind, rect in self._noise_button_rects().items():
            if rect.collidepoint(pos):
                p = self.tile_params[self.current_tile]
                if p.noise_kind != kind:
                    p.noise_kind = kind
                    changed = True

        # Случайный сид
        if self._rand_seed_rect().collidepoint(pos):
            p = self.tile_params[self.current_tile]
            p.seed = random.randint(0, 2**31 - 1)
            changed = True

        # Сброс тайла
        if self._reset_rect().collidepoint(pos):
            self.tile_params[self.current_tile] = \
                library.PRESETS[self.current_tile].copy()
            self.pattern_section = None
            self._load_params_to_widgets()
            changed = True

        # Поле имени
        if self._name_input_rect().collidepoint(pos):
            self.input_active = True
            return False

        # Библиотека
        if self._save_rect().collidepoint(pos):
            self._do_save()
            return False
        if self._apply_rect().collidepoint(pos):
            self._do_apply()
            return False
        if self._delete_rect().collidepoint(pos):
            self._do_delete()
            return False

        # Строки списка
        for i, rect in enumerate(self._set_row_rects()):
            if rect.collidepoint(pos) and i < len(self.sets):
                self.selected_set = self.sets[i]
                return False

        return changed

    # ------------------------------------------------------------------
    # Действия библиотеки
    # ------------------------------------------------------------------
    def _do_save(self) -> None:
        name = self.input_name.strip() or f"Набор {len(self.sets) + 1}"
        self._sync_params_from_widgets()
        folder = library.save_set(name, self.tile_params)
        self.sets = library.list_sets()
        self.selected_set = folder
        self.input_name = ""
        self._toast(f"Сохранено: {folder}")

    def _do_apply(self) -> None:
        if not self.selected_set:
            self._toast("Сначала выберите набор")
            return
        library.set_active(self.selected_set)
        self._toast(f"Применено: {self.selected_set}")

    def _do_delete(self) -> None:
        if not self.selected_set:
            self._toast("Сначала выберите набор")
            return
        library.delete_set(self.selected_set)
        self.sets = library.list_sets()
        self.selected_set = None
        self._toast("Удалено")

    def _toast(self, text: str) -> None:
        self.toast = text
        self.toast_timer = 2.0

    # ------------------------------------------------------------------
    # Геометрия
    # ------------------------------------------------------------------
    def _back_rect(self) -> pygame.Rect:
        return pygame.Rect(settings.SCREEN_WIDTH - 140, 12, 120, 32)

    def _tile_button_rects(self) -> dict[int, pygame.Rect]:
        rects = {}
        tids = list(library.TILE_LABELS.keys())
        n = len(tids)
        bs, gap = 32, 4
        total = n * bs + (n - 1) * gap
        x0 = (self.LEFT_W - total) // 2
        for i, tid in enumerate(tids):
            rects[tid] = pygame.Rect(x0 + i * (bs + gap), 76, bs, bs)
        return rects

    def _size_button_rects(self) -> dict[int, pygame.Rect]:
        x0, y, w, h, gap = 24, 150, 60, 28, 8
        return {s: pygame.Rect(x0 + i * (w + gap), y, w, h)
                for i, s in enumerate((16, 32, 64))}

    def _noise_button_rects(self) -> dict[str, pygame.Rect]:
        x0, y, h, gap = 24, 204, 28, 8
        widths = {"value": 70, "worley": 76, "white": 68}
        rects = {}
        cur = x0
        for kind, w in widths.items():
            rects[kind] = pygame.Rect(cur, y, w, h)
            cur += w + gap
        return rects

    def _rand_seed_rect(self) -> pygame.Rect:
        return pygame.Rect(24, 240, 150, 28)

    def _reset_rect(self) -> pygame.Rect:
        return pygame.Rect(184, 240, 140, 28)

    def _name_input_rect(self) -> pygame.Rect:
        return pygame.Rect(980, 500, 280, 32)

    def _save_rect(self) -> pygame.Rect:
        return pygame.Rect(980, 550, 280, 36)

    def _apply_rect(self) -> pygame.Rect:
        return pygame.Rect(980, 596, 280, 36)

    def _delete_rect(self) -> pygame.Rect:
        return pygame.Rect(980, 642, 280, 36)

    def _set_row_rects(self) -> list[pygame.Rect]:
        return [pygame.Rect(970, 110 + i * 30, 300, 26) for i in range(12)]

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        self.screen.fill((18, 20, 30))

        # Шапка
        pygame.draw.rect(self.screen, (26, 28, 40),
                         (0, 0, settings.SCREEN_WIDTH, self.TOP))
        pygame.draw.line(self.screen, (70, 78, 100),
                         (0, self.TOP), (settings.SCREEN_WIDTH, self.TOP), 2)
        title = self.font_h1.render("Генератор текстур", True, (200, 220, 240))
        self.screen.blit(title, (20, 16))

        back = self._back_rect()
        pygame.draw.rect(self.screen, (60, 64, 80), back, border_radius=4)
        pygame.draw.rect(self.screen, (110, 118, 140), back, 2, border_radius=4)
        bt = self.font_med.render("← Назад", True, (230, 230, 230))
        self.screen.blit(bt, bt.get_rect(center=back.center))

        # Разделители
        pygame.draw.line(self.screen, (60, 64, 80),
                         (self.LEFT_W, self.TOP),
                         (self.LEFT_W, settings.SCREEN_HEIGHT), 1)
        pygame.draw.line(self.screen, (60, 64, 80),
                         (960, self.TOP),
                         (960, settings.SCREEN_HEIGHT), 1)

        self._draw_left_panel()
        self._draw_center_panel()
        self._draw_right_panel()
        self._draw_toast()

        # Панели colorpicker'ов поверх всего
        for cp in self.color_pickers.values():
            cp.draw_panel(self.screen)

    def _draw_left_panel(self) -> None:
        # Плитки блоков
        self.screen.blit(self.font_h2.render("Блок", True, (200, 220, 240)),
                         (24, 60))

        for tid, rect in self._tile_button_rects().items():
            selected = (tid == self.current_tile)
            color = (140, 210, 130) if selected else (60, 64, 80)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, (110, 118, 140), rect, 2, border_radius=4)
            mini = generate_surface(self.tile_params[tid])
            mini = pygame.transform.scale(mini, (28, 28))
            self.screen.blit(mini, (rect.x + 2, rect.y + 2))
            lbl = self.font_tiny.render(library.TILE_LABELS[tid], True,
                                        (220, 220, 220))
            self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                   rect.bottom + 2))

        # Размер
        self.screen.blit(self.font_small.render("Размер", True, (200, 200, 210)),
                         (24, 132))
        p = self.tile_params[self.current_tile]
        for size, rect in self._size_button_rects().items():
            selected = (size == p.size)
            color = (140, 210, 130) if selected else (60, 64, 80)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, (110, 118, 140), rect, 2, border_radius=4)
            lbl = self.font_small.render(str(size), True, (230, 230, 230))
            self.screen.blit(lbl, lbl.get_rect(center=rect.center))

        # Шум
        self.screen.blit(self.font_small.render("Шум", True, (200, 200, 210)),
                         (24, 186))
        for kind, rect in self._noise_button_rects().items():
            selected = (kind == p.noise_kind)
            color = (140, 210, 130) if selected else (60, 64, 80)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, (110, 118, 140), rect, 2, border_radius=4)
            lbl = self.font_small.render(kind, True, (230, 230, 230))
            self.screen.blit(lbl, lbl.get_rect(center=rect.center))

        # Утилитные кнопки
        r1 = self._rand_seed_rect()
        pygame.draw.rect(self.screen, (60, 64, 80), r1, border_radius=4)
        pygame.draw.rect(self.screen, (110, 118, 140), r1, 2, border_radius=4)
        t1 = self.font_small.render("Случайный сид", True, (230, 230, 230))
        self.screen.blit(t1, t1.get_rect(center=r1.center))

        r2 = self._reset_rect()
        pygame.draw.rect(self.screen, (60, 64, 80), r2, border_radius=4)
        pygame.draw.rect(self.screen, (110, 118, 140), r2, 2, border_radius=4)
        t2 = self.font_small.render("Сбросить", True, (230, 230, 230))
        self.screen.blit(t2, t2.get_rect(center=r2.center))

        # Основные слайдеры
        for s in self.sliders.values():
            s.draw(self.screen, self.font_small)

        # Заголовок «Узоры»
        self.screen.blit(self.font_h2.render("Узоры", True, (200, 220, 240)),
                         (24, 460))

        # Чекбоксы и color pickers
        for key, cb in self.checkboxes.items():
            cb.draw(self.screen, self.font_small)
        for cp in self.color_pickers.values():
            cp.draw(self.screen)

        # Слайдеры узоров — если раскрыта секция
        if self.pattern_section:
            for s in self.pattern_sliders.values():
                s.draw(self.screen, self.font_small)

    def _draw_center_panel(self) -> None:
        p = self.tile_params[self.current_tile]

        title = f"{library.TILE_LABELS[self.current_tile]}  ·  " \
                f"{p.size}×{p.size}  ·  сид {p.seed}"
        surf = self.font_h2.render(title, True, (200, 220, 240))
        self.screen.blit(surf, (380, 70))

        big_size = 288
        big_x = self.LEFT_W + (600 - big_size) // 2
        big_y = 108
        big_frame = pygame.Rect(big_x, big_y, big_size, big_size)
        pygame.draw.rect(self.screen, (30, 34, 46), big_frame, border_radius=6)
        pygame.draw.rect(self.screen, (70, 78, 100), big_frame, 2, border_radius=6)
        if self._preview_surf is not None:
            big = pygame.transform.scale(self._preview_surf,
                                         (big_size - 16, big_size - 16))
            self.screen.blit(big, (big_frame.x + 8, big_frame.y + 8))

        y0 = 420
        self.screen.blit(self.font_h2.render("Вариации сида",
                                             True, (200, 220, 240)),
                         (380, y0 - 26))

        cell, gap = 96, 10
        total = 3 * cell + 2 * gap
        x0 = self.LEFT_W + (600 - total) // 2
        for i, v in enumerate(self._variations):
            r = i // 3
            c = i % 3
            rx = x0 + c * (cell + gap)
            ry = y0 + r * (cell + gap)
            frame = pygame.Rect(rx, ry, cell, cell)
            pygame.draw.rect(self.screen, (30, 34, 46), frame, border_radius=4)
            pygame.draw.rect(self.screen, (70, 78, 100), frame, 2, border_radius=4)
            scaled = pygame.transform.scale(v, (cell - 8, cell - 8))
            self.screen.blit(scaled, (rx + 4, ry + 4))

    def _draw_right_panel(self) -> None:
        self.screen.blit(self.font_h2.render("Библиотека наборов",
                                             True, (200, 220, 240)),
                         (980, 70))

        for i, rect in enumerate(self._set_row_rects()):
            if i >= len(self.sets):
                break
            name = self.sets[i]
            selected = (name == self.selected_set)
            bg = (60, 90, 60) if selected else (40, 44, 56)
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, (70, 78, 100), rect, 1, border_radius=4)
            active = library.get_active() == name
            label = ("● " if active else "  ") + name
            color = (180, 240, 160) if active else (220, 220, 220)
            s = self.font_small.render(label, True, color)
            self.screen.blit(s, (rect.x + 8, rect.y + 4))

        lbl = self.font_small.render("Имя набора:", True, (200, 200, 210))
        self.screen.blit(lbl, (980, 478))
        rect = self._name_input_rect()
        border = (140, 210, 130) if self.input_active else (70, 78, 100)
        pygame.draw.rect(self.screen, (30, 34, 46), rect, border_radius=4)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=4)
        shown = self.input_name
        if self.input_active and int(pygame.time.get_ticks() / 500) % 2 == 0:
            shown += "|"
        s = self.font_med.render(shown, True, (240, 240, 240))
        self.screen.blit(s, (rect.x + 8, rect.centery - s.get_height() // 2))

        for rect_, label, color in (
            (self._save_rect(),   "Сохранить набор",             (140, 210, 130)),
            (self._apply_rect(),  "Применить как активный",      (140, 190, 220)),
            (self._delete_rect(), "Удалить",                     (170, 70, 70)),
        ):
            pygame.draw.rect(self.screen, color, rect_, border_radius=4)
            pygame.draw.rect(self.screen, (110, 118, 140), rect_, 2, border_radius=4)
            text_color = (18, 20, 30) if color != (170, 70, 70) else (240, 240, 240)
            t = self.font_med.render(label, True, text_color)
            self.screen.blit(t, t.get_rect(center=rect_.center))

    def _draw_toast(self) -> None:
        if self.toast_timer <= 0:
            return
        s = self.font_med.render(self.toast, True, (240, 240, 240))
        pad = 12
        rect = s.get_rect()
        rect.inflate_ip(pad * 2, pad)
        rect.midbottom = (settings.SCREEN_WIDTH // 2,
                          settings.SCREEN_HEIGHT - 20)
        pygame.draw.rect(self.screen, (26, 28, 40), rect, border_radius=6)
        pygame.draw.rect(self.screen, (140, 210, 130), rect, 2, border_radius=6)
        self.screen.blit(s, s.get_rect(center=rect.center))
        
        