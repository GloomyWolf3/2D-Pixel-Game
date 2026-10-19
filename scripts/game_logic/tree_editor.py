# scripts/game_logic/tree_editor.py
"""Экран «Генератор деревьев»."""
from __future__ import annotations

import colorsys
import random

import pygame

from scripts.config import settings
from scripts.texture_gen import tree_library
from scripts.texture_gen.tree_generator import generate_tree_surface
from scripts.texture_gen.tree_params import (
    TreeParams, PRESETS, LABELS, CROWN_TYPES, CROWN_LABELS,
)


class Slider:
    def __init__(self, x, y, w, label, min_v, max_v, value, fmt="{:.2f}", step=None):
        self.rect = pygame.Rect(x, y, w, 8)
        self.hit = pygame.Rect(x - 8, y - 14, w + 16, 30)
        self.label = label
        self.min_v, self.max_v = min_v, max_v
        self.value = float(value)
        self.fmt = fmt
        self.step = step
        self.dragging = False

    def _to_x(self, v):
        t = (v - self.min_v) / (self.max_v - self.min_v)
        return self.rect.x + int(t * self.rect.w)

    def _from_x(self, x):
        t = max(0.0, min(1.0, (x - self.rect.x) / max(1, self.rect.w)))
        v = self.min_v + t * (self.max_v - self.min_v)
        if self.step:
            v = round(v / self.step) * self.step
        return v

    def handle(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hit.collidepoint(event.pos):
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
        s = font.render(f"{self.label}: {self.fmt.format(self.value)}", True, (220, 220, 220))
        surface.blit(s, (self.rect.x, self.rect.y - 18))
        pygame.draw.rect(surface, (60, 64, 80), self.rect, border_radius=3)
        t = (self.value - self.min_v) / (self.max_v - self.min_v)
        fill = pygame.Rect(self.rect.x, self.rect.y, int(t * self.rect.w), self.rect.h)
        pygame.draw.rect(surface, (140, 210, 130), fill, border_radius=3)
        kx = self._to_x(self.value)
        pygame.draw.circle(surface, (240, 240, 240), (kx, self.rect.centery), 6)
        pygame.draw.circle(surface, (40, 44, 56), (kx, self.rect.centery), 6, 2)


class Checkbox:
    def __init__(self, x, y, label, value):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.label = label
        self.value = value

    def handle(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.inflate(160, 6).collidepoint(event.pos):
                self.value = not self.value
                return True
        return False

    def draw(self, surface, font):
        pygame.draw.rect(surface, (40, 44, 56), self.rect, border_radius=3)
        pygame.draw.rect(surface, (110, 118, 140), self.rect, 2, border_radius=3)
        if self.value:
            pygame.draw.line(surface, (180, 240, 160), (self.rect.x + 4, self.rect.centery), (self.rect.centerx, self.rect.bottom - 5), 3)
            pygame.draw.line(surface, (180, 240, 160), (self.rect.centerx, self.rect.bottom - 5), (self.rect.right - 4, self.rect.y + 4), 3)
        s = font.render(self.label, True, (220, 220, 220))
        surface.blit(s, (self.rect.right + 8, self.rect.y + 2))


class ColorPicker:
    CELL = 20
    COLS, ROWS = 8, 4

    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, 30, 22)
        self.color = tuple(color)
        self.open = False
        self.palette = self._build()

    @staticmethod
    def _build():
        out = []
        for row in range(3):
            s = 1.0 - row * 0.30
            v = 1.0 - row * 0.15
            for col in range(8):
                r, g, b = colorsys.hsv_to_rgb(col / 8.0, s, v)
                out.append((int(r * 255), int(g * 255), int(b * 255)))
        for g in (15, 60, 110, 160, 200, 240, 255, 0):
            out.append((g, g, g))
        return out

    def panel(self):
        return pygame.Rect(self.rect.x, self.rect.y + self.rect.h + 4, self.COLS * self.CELL, self.ROWS * self.CELL)

    def handle(self, event) -> bool:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.open:
            p = self.panel()
            if p.collidepoint(event.pos):
                c = (event.pos[0] - p.x) // self.CELL
                r = (event.pos[1] - p.y) // self.CELL
                idx = r * self.COLS + c
                if 0 <= idx < len(self.palette):
                    self.color = self.palette[idx]
                    self.open = False
                    return True
            self.open = False
            return False
        if self.rect.collidepoint(event.pos):
            self.open = True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=3)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 2, border_radius=3)

    def draw_panel(self, surface):
        if not self.open:
            return
        p = self.panel()
        pygame.draw.rect(surface, (20, 22, 30), p, border_radius=4)
        pygame.draw.rect(surface, (110, 118, 140), p, 2, border_radius=4)
        for idx, col in enumerate(self.palette):
            r = idx // self.COLS
            c = idx % self.COLS
            pygame.draw.rect(surface, col, (p.x + c * self.CELL + 2, p.y + r * self.CELL + 2, self.CELL - 4, self.CELL - 4))


class TreeEditor:
    TOP = 56
    LEFT_W = 300
    RIGHT_W = 300

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True

        self.params: dict[str, TreeParams] = {k: p.copy() for k, p in PRESETS.items()}
        self.current_kind = "oak"
        self.tab = "trunk"

        self.font_h1 = settings.get_font(24, bold=True)
        self.font_h2 = settings.get_font(18, bold=True)
        self.font_med = settings.get_font(16)
        self.font_small = settings.get_font(14)
        self.font_tiny = settings.get_font(12)

        self.sets = tree_library.list_tree_sets()
        self.selected_set: str | None = None
        self.input_name = ""
        self.input_active = False

        self.toast = ""
        self.toast_timer = 0.0

        self._preview = None
        self._preview_key = None

        self._build_widgets()
        self._refresh_preview()

    def _build_widgets(self):
        p = self.params[self.current_kind]
        sx = 20
        sw = self.LEFT_W - 40

        self.sliders = {
            "trunk_h": Slider(sx, 320, sw, "Высота ствола", 20, 130, p.trunk_h, "{:.0f}", 1),
            "trunk_w": Slider(sx, 358, sw, "Толщина ствола", 2, 16, p.trunk_w, "{:.0f}", 1),
            "trunk_taper": Slider(sx, 396, sw, "Сужение к верху", 0.0, 0.8, p.trunk_taper),
            
            "branches": Slider(sx, 320, sw, "Кол-во веток", 0, 10, p.branches, "{:.0f}", 1),
            "branch_angle": Slider(sx, 358, sw, "Угол веток", 10, 80, p.branch_angle, "{:.0f}", 1),
            "branch_len": Slider(sx, 396, sw, "Длина веток", 4, 40, p.branch_len, "{:.0f}", 1),
            "branch_thickness": Slider(sx, 434, sw, "Толщина веток", 1, 6, p.branch_thickness, "{:.0f}", 1),
            
            "crown_w": Slider(sx, 320, sw, "Ширина кроны", 8, 160, p.crown_w, "{:.0f}", 1),
            "crown_h": Slider(sx, 358, sw, "Высота кроны", 8, 160, p.crown_h, "{:.0f}", 1),
            "crown_y_offset": Slider(sx, 396, sw, "Смещение кроны", -40, 40, p.crown_y_offset, "{:.0f}", 1),
            "crown_fill": Slider(sx, 434, sw, "Заполнение", 0.0, 1.0, p.crown_fill),
            "crown_holes": Slider(sx, 472, sw, "Дыры внутри", 0.0, 0.8, p.crown_holes),
            "crown_irregularity": Slider(sx, 510, sw, "Рваность краев", 0.0, 1.0, p.crown_irregularity),
            "leaf_pixel": Slider(sx, 548, sw, "Размер пикселя листвы", 1, 8, p.leaf_pixel, "{:.0f}", 1),
            
            "var_count": Slider(sx, 320, sw, "Кол-во вариаций", 2, 16, p.variants_count, "{:.0f}", 1),
            "var_trunk_h_min": Slider(sx, 355, sw, "Мин. высота ствола", 20, 130, p.var_trunk_h[0], "{:.0f}", 1),
            "var_trunk_h_max": Slider(sx, 385, sw, "Макс. высота ствола", 20, 130, p.var_trunk_h[1], "{:.0f}", 1),
            "var_crown_w_min": Slider(sx, 420, sw, "Мин. ширина кроны", 8, 160, p.var_crown_w[0], "{:.0f}", 1),
            "var_crown_w_max": Slider(sx, 450, sw, "Макс. ширина кроны", 8, 160, p.var_crown_w[1], "{:.0f}", 1),
            "var_crown_h_min": Slider(sx, 485, sw, "Мин. высота кроны", 8, 160, p.var_crown_h[0], "{:.0f}", 1),
            "var_crown_h_max": Slider(sx, 515, sw, "Макс. высота кроны", 8, 160, p.var_crown_h[1], "{:.0f}", 1),
            "var_crown_irregularity_min": Slider(sx, 550, sw, "Мин. рваность", 0.0, 1.0, p.var_crown_irregularity[0]),
            "var_crown_irregularity_max": Slider(sx, 580, sw, "Макс. рваность", 0.0, 1.0, p.var_crown_irregularity[1]),
            "var_crown_holes_min": Slider(sx, 615, sw, "Мин. дыры", 0.0, 0.8, p.var_crown_holes[0]),
            "var_crown_holes_max": Slider(sx, 645, sw, "Макс. дыры", 0.0, 0.8, p.var_crown_holes[1]),
        }

        self.groups = {
            "trunk":    ["trunk_h", "trunk_w", "trunk_taper"],
            "branches": ["branches", "branch_angle", "branch_len", "branch_thickness"],
            "crown":    ["crown_w", "crown_h", "crown_y_offset", "crown_fill", "crown_holes", "crown_irregularity", "leaf_pixel"],
            "colors":   [],
            "variations": ["var_count", "var_trunk_h_min", "var_trunk_h_max", "var_crown_w_min", "var_crown_w_max", "var_crown_h_min", "var_crown_h_max", "var_crown_irregularity_min", "var_crown_irregularity_max", "var_crown_holes_min", "var_crown_holes_max"],
        }

        self.color_pickers = {
            "trunk": ColorPicker(sx + 200, 500, p.trunk_color),
            "leaf":  ColorPicker(sx + 200, 530, p.leaf_color),
            "leaf2": ColorPicker(sx + 200, 560, p.leaf_color2),
        }

        self.checkboxes = {
            "bark_lines": Checkbox(sx, 680, "Борозды на стволе", p.bark_lines),
            "show_bounds": Checkbox(sx + 150, 680, "Контур", True),
        }

    def _sync_from_widgets(self):
        p = self.params[self.current_kind]
        p.trunk_h = int(self.sliders["trunk_h"].value)
        p.trunk_w = int(self.sliders["trunk_w"].value)
        p.trunk_taper = self.sliders["trunk_taper"].value
        p.branches = int(self.sliders["branches"].value)
        p.branch_angle = self.sliders["branch_angle"].value
        p.branch_len = self.sliders["branch_len"].value
        p.branch_thickness = int(self.sliders["branch_thickness"].value)
        p.crown_w = int(self.sliders["crown_w"].value)
        p.crown_h = int(self.sliders["crown_h"].value)
        p.crown_y_offset = int(self.sliders["crown_y_offset"].value)
        p.crown_fill = self.sliders["crown_fill"].value
        p.crown_holes = self.sliders["crown_holes"].value
        p.crown_irregularity = self.sliders["crown_irregularity"].value
        p.leaf_pixel = int(self.sliders["leaf_pixel"].value)
        
        p.variants_count = int(self.sliders["var_count"].value)
        p.var_trunk_h = (self.sliders["var_trunk_h_min"].value, self.sliders["var_trunk_h_max"].value)
        p.var_crown_w = (self.sliders["var_crown_w_min"].value, self.sliders["var_crown_w_max"].value)
        p.var_crown_h = (self.sliders["var_crown_h_min"].value, self.sliders["var_crown_h_max"].value)
        p.var_crown_irregularity = (self.sliders["var_crown_irregularity_min"].value, self.sliders["var_crown_irregularity_max"].value)
        p.var_crown_holes = (self.sliders["var_crown_holes_min"].value, self.sliders["var_crown_holes_max"].value)
        
        p.trunk_color = tuple(self.color_pickers["trunk"].color)
        p.leaf_color = tuple(self.color_pickers["leaf"].color)
        p.leaf_color2 = tuple(self.color_pickers["leaf2"].color)
        p.bark_lines = self.checkboxes["bark_lines"].value

    def _load_to_widgets(self):
        p = self.params[self.current_kind]
        self.sliders["trunk_h"].value = float(p.trunk_h)
        self.sliders["trunk_w"].value = float(p.trunk_w)
        self.sliders["trunk_taper"].value = p.trunk_taper
        self.sliders["branches"].value = float(p.branches)
        self.sliders["branch_angle"].value = p.branch_angle
        self.sliders["branch_len"].value = p.branch_len
        self.sliders["branch_thickness"].value = float(p.branch_thickness)
        self.sliders["crown_w"].value = float(p.crown_w)
        self.sliders["crown_h"].value = float(p.crown_h)
        self.sliders["crown_y_offset"].value = float(p.crown_y_offset)
        self.sliders["crown_fill"].value = p.crown_fill
        self.sliders["crown_holes"].value = p.crown_holes
        self.sliders["crown_irregularity"].value = p.crown_irregularity
        self.sliders["leaf_pixel"].value = float(p.leaf_pixel)
        
        self.sliders["var_count"].value = float(p.variants_count)
        self.sliders["var_trunk_h_min"].value = p.var_trunk_h[0]
        self.sliders["var_trunk_h_max"].value = p.var_trunk_h[1]
        self.sliders["var_crown_w_min"].value = p.var_crown_w[0]
        self.sliders["var_crown_w_max"].value = p.var_crown_w[1]
        self.sliders["var_crown_h_min"].value = p.var_crown_h[0]
        self.sliders["var_crown_h_max"].value = p.var_crown_h[1]
        self.sliders["var_crown_irregularity_min"].value = p.var_crown_irregularity[0]
        self.sliders["var_crown_irregularity_max"].value = p.var_crown_irregularity[1]
        self.sliders["var_crown_holes_min"].value = p.var_crown_holes[0]
        self.sliders["var_crown_holes_max"].value = p.var_crown_holes[1]
        
        self.color_pickers["trunk"].color = tuple(p.trunk_color)
        self.color_pickers["leaf"].color = tuple(p.leaf_color)
        self.color_pickers["leaf2"].color = tuple(p.leaf_color2)
        self.checkboxes["bark_lines"].value = p.bark_lines

    def _refresh_preview(self):
        self._sync_from_widgets()
        p = self.params[self.current_kind]
        key = (self.current_kind, p.seed, p.size_w, p.size_h,
               p.trunk_h, p.trunk_w, round(p.trunk_taper, 3),
               p.branches, round(p.branch_angle, 2), round(p.branch_len, 2),
               p.branch_thickness, p.crown_type, p.crown_w, p.crown_h, p.crown_y_offset,
               round(p.crown_fill, 3), round(p.crown_holes, 3), round(p.crown_irregularity, 3),
               p.leaf_pixel, tuple(p.trunk_color), tuple(p.leaf_color), tuple(p.leaf_color2),
               p.bark_lines)
        if key != self._preview_key:
            self._preview = generate_tree_surface(p)
            self._preview_key = key

    def run(self):
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self._handle(event)
            if self.toast_timer > 0:
                self.toast_timer -= dt
            self._draw()
            pygame.display.flip()

    def _handle(self, event):
        if self.input_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.input_name = self.input_name[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.input_active = False
                elif event.unicode and event.unicode.isprintable() and len(self.input_name) < 32:
                    self.input_name += event.unicode
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_rect().collidepoint(event.pos):
                self.running = False
                return

        for cp in self.color_pickers.values():
            if cp.handle(event):
                self._refresh_preview()
                return

        changed = False
        for key in self.groups[self.tab]:
            if self.sliders[key].handle(event):
                changed = True

        for cb in self.checkboxes.values():
            if cb.handle(event):
                changed = True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_clicks(event.pos):
                changed = True

        if changed:
            self._refresh_preview()

    def _handle_clicks(self, pos) -> bool:
        for kind, rect in self._kind_buttons().items():
            if rect.collidepoint(pos):
                self.current_kind = kind
                self._load_to_widgets()
                return True

        for tab, rect in self._tab_buttons().items():
            if rect.collidepoint(pos):
                self.tab = tab
                return False

        for kind, rect in self._crown_buttons().items():
            if rect.collidepoint(pos):
                p = self.params[self.current_kind]
                if p.crown_type != kind:
                    p.crown_type = kind
                    return True

        if self._seed_rect().collidepoint(pos):
            self.params[self.current_kind].seed = random.randint(0, 2**31 - 1)
            return True

        if self._reset_rect().collidepoint(pos):
            if self.current_kind in PRESETS:
                self.params[self.current_kind] = PRESETS[self.current_kind].copy()
                self._load_to_widgets()
                return True

        if self._name_rect().collidepoint(pos):
            self.input_active = True
            return False

        if self._save_rect().collidepoint(pos):
            self._do_save()
            return False
        if self._apply_rect().collidepoint(pos):
            self._do_apply()
            return False
        if self._delete_rect().collidepoint(pos):
            self._do_delete()
            return False

        for i, rect in enumerate(self._set_rows()):
            if rect.collidepoint(pos) and i < len(self.sets):
                self.selected_set = self.sets[i]
                
                # Загружаем параметры из сохранённого набора
                loaded = tree_library.load_tree_params(self.selected_set)
                if loaded:
                    # Обновляем только те виды, что есть в наборе
                    for k, v in loaded.items():
                        self.params[k] = v
                    self._load_to_widgets()
                    self.input_name = self.selected_set
                    self.input_active = False
                    self._refresh_preview()
                return True

        return False

    def _do_save(self):
        self._sync_from_widgets()
        
        # Берем имя из поля ввода. Если пустое — задаем дефолтное
        name = self.input_name.strip() or f"Деревья {len(self.sets) + 1}"
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip() or "trees"
        
        # Сохраняем, принудительно перезаписывая папку с таким именем
        tree_library.save_tree_set(name, self.params, force_folder=safe_name)
        
        self.selected_set = safe_name
        self.input_name = safe_name
        self.sets = tree_library.list_tree_sets()
        self._toast(f"Сохранено: {safe_name}")

    def _do_apply(self):
        if not self.selected_set:
            self._toast("Выберите набор")
            return
        tree_library.set_active(self.selected_set)
        self._toast(f"Активен: {self.selected_set}")

    def _do_delete(self):
        if not self.selected_set:
            self._toast("Выберите набор")
            return
        tree_library.delete_tree_set(self.selected_set)
        self.sets = tree_library.list_tree_sets()
        self.selected_set = None
        self._toast("Удалено")

    def _toast(self, text):
        self.toast = text
        self.toast_timer = 2.0

    def _back_rect(self): return pygame.Rect(settings.SCREEN_WIDTH - 140, 12, 120, 32)

    def _kind_buttons(self):
        out = {}
        kinds = list(PRESETS.keys())
        n = len(kinds)
        bs, gap = 44, 6
        total = n * bs + (n - 1) * gap
        x0 = (self.LEFT_W - total) // 2
        for i, k in enumerate(kinds):
            out[k] = pygame.Rect(x0 + i * (bs + gap), 70, bs, bs)
        return out

    def _tab_buttons(self):
        y, h = 240, 26
        keys = ["trunk", "branches", "crown", "colors", "variations"]
        labels = {"trunk": "Ствол", "branches": "Ветки", "crown": "Крона", "colors": "Цвета", "variations": "Вариации"}
        w = (self.LEFT_W - 20) // len(keys) - 4
        out = {}
        x = 10
        for k in keys:
            out[k] = pygame.Rect(x, y, w, h)
            x += w + 4
        self._tab_labels = labels
        return out

    def _crown_buttons(self):
        out = {}
        y = 280
        w, h, gap = 62, 24, 4
        x = 20
        for k in CROWN_TYPES:
            out[k] = pygame.Rect(x, y, w, h)
            x += w + gap
        return out

    def _seed_rect(self): return pygame.Rect(20, 720, 130, 28)
    def _reset_rect(self): return pygame.Rect(160, 720, 120, 28)
    def _name_rect(self): return pygame.Rect(settings.SCREEN_WIDTH - 300, 470, 280, 30)
    def _save_rect(self): return pygame.Rect(settings.SCREEN_WIDTH - 300, 520, 280, 34)
    def _apply_rect(self): return pygame.Rect(settings.SCREEN_WIDTH - 300, 564, 280, 34)
    def _delete_rect(self): return pygame.Rect(settings.SCREEN_WIDTH - 300, 608, 280, 34)
    def _set_rows(self): return [pygame.Rect(settings.SCREEN_WIDTH - 310, 100 + i * 28, 300, 24) for i in range(12)]

    def _draw(self):
        self.screen.fill((18, 20, 30))
        pygame.draw.rect(self.screen, (26, 28, 40), (0, 0, settings.SCREEN_WIDTH, self.TOP))
        pygame.draw.line(self.screen, (70, 78, 100), (0, self.TOP), (settings.SCREEN_WIDTH, self.TOP), 2)
        title = self.font_h1.render("Генератор деревьев", True, (200, 220, 240))
        self.screen.blit(title, (20, 16))

        back = self._back_rect()
        pygame.draw.rect(self.screen, (60, 64, 80), back, border_radius=4)
        pygame.draw.rect(self.screen, (110, 118, 140), back, 2, border_radius=4)
        bt = self.font_med.render("← Назад", True, (230, 230, 230))
        self.screen.blit(bt, bt.get_rect(center=back.center))

        pygame.draw.line(self.screen, (60, 64, 80), (self.LEFT_W, self.TOP), (self.LEFT_W, settings.SCREEN_HEIGHT), 1)
        pygame.draw.line(self.screen, (60, 64, 80), (settings.SCREEN_WIDTH - self.RIGHT_W, self.TOP), (settings.SCREEN_WIDTH - self.RIGHT_W, settings.SCREEN_HEIGHT), 1)

        self._draw_left()
        self._draw_center()
        self._draw_right()

        for cp in self.color_pickers.values():
            cp.draw_panel(self.screen)

        self._draw_toast()

    def _draw_left(self):
        self.screen.blit(self.font_h2.render("Тип", True, (200, 220, 240)), (20, 46))
        for kind, rect in self._kind_buttons().items():
            selected = (kind == self.current_kind)
            bg = (140, 210, 130) if selected else (60, 64, 80)
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, (110, 118, 140), rect, 2, border_radius=4)
            lbl = self.font_tiny.render(LABELS[kind], True, (240, 240, 240))
            self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.bottom + 2))

        tabs = self._tab_buttons()
        for k, rect in tabs.items():
            selected = (k == self.tab)
            bg = (140, 210, 130) if selected else (60, 64, 80)
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, (110, 118, 140), rect, 2, border_radius=4)
            lbl = self.font_tiny.render(self._tab_labels[k], True, (240, 240, 240))
            self.screen.blit(lbl, lbl.get_rect(center=rect.center))

        if self.tab == "crown":
            self.screen.blit(self.font_small.render("Форма кроны", True, (200, 200, 210)), (20, 262))
            p = self.params[self.current_kind]
            for k, rect in self._crown_buttons().items():
                selected = (k == p.crown_type)
                bg = (140, 210, 130) if selected else (60, 64, 80)
                pygame.draw.rect(self.screen, bg, rect, border_radius=4)
                pygame.draw.rect(self.screen, (110, 118, 140), rect, 2, border_radius=4)
                lbl = self.font_tiny.render(CROWN_LABELS[k], True, (240, 240, 240))
                self.screen.blit(lbl, lbl.get_rect(center=rect.center))

        for key in self.groups[self.tab]:
            self.sliders[key].draw(self.screen, self.font_small)

        if self.tab == "colors":
            self.screen.blit(self.font_small.render("Цвет ствола", True, (200, 200, 210)), (20, 500))
            self.screen.blit(self.font_small.render("Цвет листвы", True, (200, 200, 210)), (20, 530))
            self.screen.blit(self.font_small.render("Цвет листвы 2", True, (200, 200, 210)), (20, 560))

        for cb in self.checkboxes.values():
            cb.draw(self.screen, self.font_small)

        r1 = self._seed_rect()
        pygame.draw.rect(self.screen, (60, 64, 80), r1, border_radius=4)
        pygame.draw.rect(self.screen, (110, 118, 140), r1, 2, border_radius=4)
        t1 = self.font_small.render("Случ. сид", True, (230, 230, 230))
        self.screen.blit(t1, t1.get_rect(center=r1.center))

        r2 = self._reset_rect()
        pygame.draw.rect(self.screen, (60, 64, 80), r2, border_radius=4)
        pygame.draw.rect(self.screen, (110, 118, 140), r2, 2, border_radius=4)
        t2 = self.font_small.render("Сброс", True, (230, 230, 230))
        self.screen.blit(t2, t2.get_rect(center=r2.center))

    def _draw_center(self):
        cx = self.LEFT_W + (settings.SCREEN_WIDTH - self.LEFT_W - self.RIGHT_W) // 2
        p = self.params[self.current_kind]

        header = f"{LABELS[self.current_kind]}  ·  {p.size_w}×{p.size_h}  ·  сид {p.seed}"
        hs = self.font_h2.render(header, True, (200, 220, 240))
        self.screen.blit(hs, hs.get_rect(center=(cx, 90)))

        pw = int(p.size_w * 4)
        ph = int(p.size_h * 4)
        frame = pygame.Rect(cx - pw // 2, 130, pw, ph)

        for yy in range(0, ph, 16):
            for xx in range(0, pw, 16):
                c = (44, 48, 60) if ((xx // 16 + yy // 16) % 2 == 0) else (56, 60, 74)
                pygame.draw.rect(self.screen, c, (frame.x + xx, frame.y + yy, 16, 16))

        if self._preview is not None:
            big = pygame.transform.scale(self._preview, (pw, ph))
            self.screen.blit(big, frame.topleft)
        pygame.draw.rect(self.screen, (110, 118, 140), frame, 2, border_radius=4)

        if self.checkboxes["show_bounds"].value:
            lp = max(1, int(p.leaf_pixel))
            cells_w = max(3, p.crown_w // lp)
            cells_h = max(3, p.crown_h // lp)
            crop_w = cells_w * lp
            crop_h = cells_h * lp
            trunk_top_y = max(2, p.size_h - 1 - p.trunk_h)
            crown_cy = trunk_top_y + p.crown_y_offset + p.crown_h // 2
            crown_cx = p.size_w // 2
            crop_px = int(round(crown_cx - crop_w * 0.5))
            crop_py = int(round(crown_cy - crop_h * 0.5))

            bx = frame.x + crop_px * 4
            by = frame.y + crop_py * 4
            bw = crop_w * 4
            bh = crop_h * 4

            dash_len = 6
            y_top, y_bot = by, by + bh
            x_left, x_right = bx, bx + bw
            for x in range(x_left, x_right, dash_len * 2):
                pygame.draw.line(self.screen, (255, 60, 60), (x, y_top), (min(x + dash_len, x_right), y_top), 2)
                pygame.draw.line(self.screen, (255, 60, 60), (x, y_bot), (min(x + dash_len, x_right), y_bot), 2)
            for y in range(y_top, y_bot, dash_len * 2):
                pygame.draw.line(self.screen, (255, 60, 60), (x_left, y), (x_left, min(y + dash_len, y_bot)), 2)
                pygame.draw.line(self.screen, (255, 60, 60), (x_right, y), (x_right, min(y + dash_len, y_bot)), 2)

    def _draw_right(self):
        x0 = settings.SCREEN_WIDTH - self.RIGHT_W + 10
        self.screen.blit(self.font_h2.render("Библиотека", True, (200, 220, 240)), (x0, 46))

        active = tree_library.get_active()
        for i, rect in enumerate(self._set_rows()):
            if i >= len(self.sets):
                break
            name = self.sets[i]
            is_selected = (name == self.selected_set)
            bg = (60, 90, 60) if is_selected else (40, 44, 56)
            pygame.draw.rect(self.screen, bg, rect, border_radius=4)
            pygame.draw.rect(self.screen, (70, 78, 100), rect, 1, border_radius=4)
            marker = "● " if name == active else "  "
            color = (180, 240, 160) if name == active else (220, 220, 220)
            s = self.font_small.render(marker + name, True, color)
            self.screen.blit(s, (rect.x + 8, rect.y + 3))

        lbl = self.font_small.render("Имя набора:", True, (200, 200, 210))
        self.screen.blit(lbl, (settings.SCREEN_WIDTH - 300, 448))

        rect = self._name_rect()
        border = (140, 210, 130) if self.input_active else (70, 78, 100)
        pygame.draw.rect(self.screen, (30, 34, 46), rect, border_radius=4)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=4)
        shown = self.input_name
        if self.input_active and int(pygame.time.get_ticks() / 500) % 2 == 0:
            shown += "|"
        ss = self.font_med.render(shown, True, (240, 240, 240))
        self.screen.blit(ss, (rect.x + 8, rect.centery - ss.get_height() // 2))

        for rect_, label, color in (
            (self._save_rect(),   "Сохранить набор",        (140, 210, 130)),
            (self._apply_rect(),  "Применить как активный", (140, 190, 220)),
            (self._delete_rect(), "Удалить",                (170, 70, 70)),
        ):
            pygame.draw.rect(self.screen, color, rect_, border_radius=4)
            pygame.draw.rect(self.screen, (110, 118, 140), rect_, 2, border_radius=4)
            text_color = (18, 20, 30) if color != (170, 70, 70) else (240, 240, 240)
            t = self.font_med.render(label, True, text_color)
            self.screen.blit(t, t.get_rect(center=rect_.center))

    def _draw_toast(self):
        if self.toast_timer <= 0:
            return
        s = self.font_med.render(self.toast, True, (240, 240, 240))
        pad = 12
        rect = s.get_rect()
        rect.inflate_ip(pad * 2, pad)
        rect.midbottom = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT - 20)
        pygame.draw.rect(self.screen, (26, 28, 40), rect, border_radius=6)
        pygame.draw.rect(self.screen, (140, 210, 130), rect, 2, border_radius=6)
        self.screen.blit(s, s.get_rect(center=rect.center))
        
        