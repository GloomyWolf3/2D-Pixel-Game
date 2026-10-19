# scripts/game_logic/game.py
"""Игровая сцена: слои, освещение, зум, растительность, пауза."""
from __future__ import annotations

import math

import numpy as np
import pygame

from scripts.config import settings
from scripts.game_logic import lighting
from scripts.game_logic import tiles as T
from scripts.game_logic.camera import Camera
from scripts.game_logic.player import Player
from scripts.game_logic.sky import Sky
from scripts.game_logic.world import World
from scripts.game_logic.pause_menu import PauseMenu
from scripts.utils import file_utils
from scripts.world_gen.biome_gen import BIOME_NAMES


_SKY_TOP_NIGHT = (10, 12, 28)
_SKY_BOT_NIGHT = (34, 38, 66)
_SKY_TOP_DAY   = (70, 130, 200)
_SKY_BOT_DAY   = (170, 210, 240)


def _lerp_color(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _tile_variant(tx, ty, salt, n):
    h = (tx * 73856093) ^ (ty * 19349663) ^ (salt * 83492791)
    h = (h ^ (h >> 15)) & 0x7fffffff
    return h % n


class Game:
    def __init__(self, screen: pygame.Surface, save_folder: str):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.folder = save_folder
        self.meta = file_utils.load_meta(save_folder) or {"name": "?"}

        self._draw_loading("Генерация мира...")
        seed = int(self.meta.get("seed", 0))
        size = self.meta.get("size", "medium")
        noise_kind = self.meta.get("noise_kind", "value")
        self.world = World(seed, size, save_folder=save_folder,
                           noise_kind=noise_kind)

        # Игрок
        cx = self.world.width // 2
        surface_y = int(self.world.surface_y[cx])
        px = cx * settings.TILE_SIZE
        py = (surface_y - 3) * settings.TILE_SIZE
        self.player = Player(px, py)

        # Камера
        self.camera = Camera(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT,
                             zoom=2.0)
        self.camera.center_on(
            self.player.x + self.player.w * 0.5,
            self.player.y + self.player.h * 0.5,
        )

        # Время и небо
        self.time_of_day = settings.START_TIME_OF_DAY
        self.total_time = 0.0
        self.sky = Sky()

        # Шрифты
        self.font_hud = settings.get_font(16)
        self.font_hint = settings.get_font(14)
        self.font_big = settings.get_font(28, bold=True)

        # Текстуры тайлов и флоры
        self.tile_surfs = self._load_tile_surfaces()
        self.flora_sprites = self._load_flora_sprites()

        print(f"[game] world.flora={len(self.world.flora)} "
              f"sprites={sum(1 for s in self.flora_sprites if s is not None)}")

        # Буфер
        self._render_surf: pygame.Surface | None = None
        self._last_view_size = (0, 0)

        self.running = True
        self.result = "menu"
        self.show_debug = False

        file_utils.update_last_played(save_folder)

    # ------------------------------------------------------------------
    def _load_tile_surfaces(self) -> dict[int, list[pygame.Surface]]:
        from scripts.texture_gen import library
        ts = settings.TILE_SIZE
        surfs: dict[int, list[pygame.Surface]] = {}

        active = library.get_active()
        if active:
            surfs.update(library.load_surfaces(active, ts))

        for tid, color in T.TILE_COLORS.items():
            if tid in surfs and surfs[tid]:
                continue
            variants = []
            for i in range(9):
                s = pygame.Surface((ts, ts))
                shift = (i - 4) * 4
                c = tuple(max(0, min(255, ch + shift)) for ch in color)
                s.fill(c)
                variants.append(s)
            surfs[tid] = variants
        return surfs

    def _load_flora_sprites(self) -> list[pygame.Surface | None]:
        """Спрайты по каждому элементу world.flora."""
        from scripts.texture_gen import tree_library
        from scripts.texture_gen.tree_generator import generate_tree_surface
        from scripts.texture_gen.tree_params import PRESETS

        # base теперь хранит списки вариаций: dict[str, list[Surface]]
        base: dict[str, list[pygame.Surface]] = {}

        active = tree_library.get_active()
        if active:
            try:
                loaded = tree_library.load_tree_surfaces(active)
                if loaded:
                    base.update(loaded)
            except Exception as e:
                print(f"[game] не смогли загрузить набор деревьев '{active}': {e}")

        # Добавляем всё, чего не хватает, из PRESETS (по 1 вариации)
        for kind, params in PRESETS.items():
            if kind not in base or not base[kind]:
                base[kind] = [generate_tree_surface(params)]

        out: list[pygame.Surface | None] = []
        for f in self.world.flora:
            variants = base.get(f["kind"], [])
            if not variants:
                out.append(None)
                continue

            # Выбираем случайную вариацию на основе сида самого дерева
            v_idx = f["seed"] % len(variants)
            sprite = variants[v_idx]

            s = f["scale"]
            if s != 1.0:
                w = max(1, int(sprite.get_width() * s))
                h = max(1, int(sprite.get_height() * s))
                sprite = pygame.transform.scale(sprite, (w, h))
            if f["flip"]:
                sprite = pygame.transform.flip(sprite, True, False)
            out.append(sprite)
        return out

    # ------------------------------------------------------------------
    def run(self) -> str:
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            self.total_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.result = "quit"
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self._on_keydown(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._on_mousedown(event)
                elif event.type == pygame.MOUSEWHEEL:
                    self._on_wheel(event)

            self.time_of_day = (
                self.time_of_day + dt / settings.DAY_DURATION_SECONDS
            ) % 1.0

            keys = pygame.key.get_pressed()
            self.player.update(self.world, keys, dt)
            self.camera.center_on(
                self.player.x + self.player.w * 0.5,
                self.player.y + self.player.h * 0.5,
            )

            self._draw()
            pygame.display.flip()

        return self.result

    # ------------------------------------------------------------------
    def _on_keydown(self, event) -> None:
        if event.key == pygame.K_ESCAPE:
            pm = PauseMenu(self.screen, self)
            action = pm.run()
            if action == "menu":
                self.result = "menu"
                self.running = False
            elif action == "quit":
                self.result = "quit"
                self.running = False
            return
        if event.key == pygame.K_F3:
            self.show_debug = not self.show_debug
            return
        if event.key == pygame.K_t:
            if settings.CHEATS_ENABLED:
                self.time_of_day = (self.time_of_day + 1 / 24) % 1.0
            return
        if event.key == pygame.K_F5:
            self.tile_surfs = self._load_tile_surfaces()
            self.flora_sprites = self._load_flora_sprites()
            return

    def _on_wheel(self, event) -> None:
        factor = 1.15 if event.y > 0 else (1.0 / 1.15)
        self.camera.zoom_by(factor)

    def _on_mousedown(self, event) -> None:
        mx, my = event.pos
        rx = mx / self.camera.zoom
        ry = my / self.camera.zoom
        wx, wy = self.camera.screen_to_world(rx, ry)
        tx = int(wx // settings.TILE_SIZE)
        ty = int(wy // settings.TILE_SIZE)
        if event.button == 1:
            self._dig(tx, ty)

    def _dig(self, tx: int, ty: int) -> None:
        current = self.world.get_tile(tx, ty)
        if current == T.AIR or current == T.BEDROCK:
            return
        self.world.set_tile(tx, ty, T.AIR)

    # ------------------------------------------------------------------
    def _day_factor(self) -> float:
        t = self.time_of_day
        raw = (1.0 - math.cos(2.0 * math.pi * t)) * 0.5
        return min(1.0, raw * 1.15)

    def _sky_light_level(self) -> float:
        d = self._day_factor()
        shaped = max(0.0, (d - 0.20) / 0.80) ** 1.2
        return 0.02 + 0.98 * shaped

    def _moon_phase(self) -> float:
        cycle = settings.DAY_DURATION_SECONDS * 8
        return (self.total_time / cycle) % 1.0

    # ------------------------------------------------------------------
    def _get_render_surface(self) -> pygame.Surface:
        vw = int(self.camera.view_w)
        vh = int(self.camera.view_h)
        if self._render_surf is None or self._last_view_size != (vw, vh):
            self._render_surf = pygame.Surface((vw, vh))
            self._last_view_size = (vw, vh)
        return self._render_surf

    def _visible_bounds(self) -> tuple[int, int, int, int]:
        ts = settings.TILE_SIZE
        tx0 = max(0, int(self.camera.x // ts) - 1)
        ty0 = max(0, int(self.camera.y // ts) - 1)
        tx1 = min(self.world.width,
                  int((self.camera.x + self.camera.view_w) // ts) + 2)
        ty1 = min(self.world.height,
                  int((self.camera.y + self.camera.view_h) // ts) + 2)
        return tx0, ty0, tx1, ty1

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        surf = self._get_render_surface()
        vw, vh = surf.get_size()

        self._draw_sky(surf, vw, vh)

        tx0, ty0, tx1, ty1 = self._visible_bounds()
        tiles_slice = self.world.tiles[tx0:tx1, ty0:ty1]
        sky_slice = self.world.sky_mask[tx0:tx1, ty0:ty1]

        self._draw_background(surf, tx0, ty0, tx1, ty1)
        self._draw_tiles(surf, tiles_slice, tx0, ty0)
        self._draw_flora(surf, tx0, tx1, ty0, ty1)

        self.player.draw(surf, self.camera.x, self.camera.y)
        self._draw_lighting(surf, tiles_slice, sky_slice, tx0, ty0)

        if (vw, vh) == (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT):
            self.screen.blit(surf, (0, 0))
        else:
            scaled = pygame.transform.scale(
                surf, (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
            self.screen.blit(scaled, (0, 0))

        self._draw_hud()
        if self.show_debug:
            self._draw_debug()

    # ------------------------------------------------------------------
    def _draw_sky(self, surf, vw, vh):
        d = self._day_factor()
        top = _lerp_color(_SKY_TOP_NIGHT, _SKY_TOP_DAY, d)
        bot = _lerp_color(_SKY_BOT_NIGHT, _SKY_BOT_DAY, d)

        step = 4
        for y in range(0, vh, step):
            t = y / max(1, vh)
            c = _lerp_color(top, bot, t)
            pygame.draw.rect(surf, c, (0, y, vw, step))

        ts = settings.TILE_SIZE
        ptx = int((self.player.x + self.player.w * 0.5) // ts)
        ptx = max(0, min(self.world.width - 1, ptx))
        surface_world_y = int(self.world.surface_y[ptx]) * ts
        horizon_y = surface_world_y - self.camera.y

        self.sky.draw(surf, self.time_of_day, vw, horizon_y, self._moon_phase())

    # ------------------------------------------------------------------
    def _draw_background(self, surf, tx0, ty0, tx1, ty1):
        vw = tx1 - tx0
        vh = ty1 - ty0
        if vw <= 0 or vh <= 0:
            return

        ts = settings.TILE_SIZE
        w = self.world.width

        bg = np.zeros((vw, vh, 3), dtype=np.uint8)
        tx_hi = min(tx1, w)
        tys = np.arange(ty0, ty1, dtype=np.float32)

        for i in range(tx_hi - tx0):
            tx = tx0 + i
            sy = int(self.world.surface_y[tx])
            top = self.world.bg_top[tx].astype(np.float32)
            bot = self.world.bg_bot[tx].astype(np.float32)
            depths_local = np.clip(tys - sy, 0.0, None)
            t = np.clip(depths_local / 60.0, 0.0, 1.0)[:, None]
            colors = top[None, :] * (1 - t) + bot[None, :] * t
            bg[i] = colors.astype(np.uint8)

        sky_slice = self.world.sky_mask[tx0:tx_hi, ty0:ty1]
        alpha = np.where(sky_slice, 0, 255).astype(np.uint8)

        mini = pygame.Surface((vw, vh), pygame.SRCALPHA)
        arr = pygame.surfarray.pixels3d(mini)
        arr[:, :, :] = bg
        del arr
        a = pygame.surfarray.pixels_alpha(mini)
        a[:, :] = alpha
        del a

        scaled = pygame.transform.scale(mini, (vw * ts, vh * ts))
        sx = tx0 * ts - self.camera.x
        sy_screen = ty0 * ts - self.camera.y
        surf.blit(scaled, (sx, sy_screen))

    # ------------------------------------------------------------------
    def _draw_tiles(self, surf, tiles_slice, tx0, ty0):
        ts = settings.TILE_SIZE
        cam_x = self.camera.x
        cam_y = self.camera.y
        blit = surf.blit
        cache = self.tile_surfs
        salt = self.world.seed & 0xff

        vw, vh = tiles_slice.shape
        screen_h = surf.get_height()
        screen_w = surf.get_width()

        for j in range(vh):
            ty = ty0 + j
            sy = ty * ts - cam_y
            if sy < -ts or sy > screen_h:
                continue
            for i in range(vw):
                tid = int(tiles_slice[i, j])
                if tid == T.AIR:
                    continue
                variants = cache.get(tid)
                if not variants:
                    continue
                tx = tx0 + i
                sx = tx * ts - cam_x
                if sx < -ts or sx > screen_w:
                    continue
                idx = _tile_variant(tx, ty, salt, len(variants))
                blit(variants[idx], (sx, sy))

    # ------------------------------------------------------------------
    def _draw_flora(self, surf, tx0, tx1, ty0, ty1):
        ts = settings.TILE_SIZE
        cam_x = self.camera.x
        cam_y = self.camera.y
        screen_w = surf.get_width()
        screen_h = surf.get_height()

        for i, f in enumerate(self.world.flora):
            tx = f["tx"]
            ty = f["ty"]

            # Деревья теперь ОЧЕНЬ большие (масштаб 3.5+), 
            # поэтому увеличиваем отсев до 40 тайлов (было 12)
            if tx < tx0 - 40 or tx > tx1 + 40:
                continue
            
            # По вертикали тоже делаем запас, так как крона высокая
            if ty < ty0 - 40 or ty > ty1 + 10:
                continue

            if i >= len(self.flora_sprites):
                continue
            sprite = self.flora_sprites[i]
            if sprite is None:
                continue

            sw = sprite.get_width()
            sh = sprite.get_height()
            base_x = tx * ts + ts // 2 - cam_x
            base_y = ty * ts + ts - cam_y     # низ спрайта = низ тайла
            px = int(base_x - sw // 2)
            py = int(base_y - sh)

            if px + sw < 0 or px > screen_w:
                continue
            if py + sh < 0 or py > screen_h:
                continue

            surf.blit(sprite, (px, py))

    # ------------------------------------------------------------------
    def _draw_lighting(self, surf, tiles_slice, sky_slice, tx0, ty0):
        vw, vh = tiles_slice.shape
        if vw == 0 or vh == 0:
            return

        ts = settings.TILE_SIZE
        sky_level = self._sky_light_level()

        ptx = (self.player.x + self.player.w * 0.5) / ts - tx0
        pty = (self.player.y + self.player.h * 0.5) / ts - ty0

        light = lighting.compute_light_map(
            tiles_slice, sky_slice, sky_level, ptx, pty,
            player_radius=13.0,
        )
        darkness = ((1.0 - light) * 255.0).astype(np.uint8)

        mini = pygame.Surface((vw, vh), pygame.SRCALPHA)
        rgb = pygame.surfarray.pixels3d(mini)
        rgb[:, :, :] = 0
        del rgb
        alpha = pygame.surfarray.pixels_alpha(mini)
        alpha[:, :] = darkness
        del alpha

        scaled = pygame.transform.scale(mini, (vw * ts, vh * ts))
        sx = tx0 * ts - self.camera.x
        sy = ty0 * ts - self.camera.y
        surf.blit(scaled, (sx, sy))

    # ------------------------------------------------------------------
    def _draw_hud(self):
        name = self.meta.get("name", "?")
        noise_kind = self.meta.get("noise_kind", "value")
        biome = self.world.biome_at(
            int((self.player.x + self.player.w * 0.5) // settings.TILE_SIZE))

        hours = self.time_of_day * 24.0
        hh = int(hours)
        mm = int((hours - hh) * 60)
        clock = f"{hh:02d}:{mm:02d}"

        text = (f"Мир: {name}   |   Биом: {BIOME_NAMES.get(biome, '?')}   "
                f"|   Время: {clock}   |   Шум: {noise_kind}   "
                f"|   Сид: {self.world.seed}")
        sf = self.font_hud.render(text, True, (240, 240, 240))
        bg = pygame.Surface((sf.get_width() + 16, sf.get_height() + 8),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 130))
        self.screen.blit(bg, (8, 8))
        self.screen.blit(sf, (16, 12))

        hint = ("A/D — движение,  Space — прыжок,  ЛКМ — копать,  "
                "Колесо — зум,  ESC — пауза,  F3 — отладка")
        hs = self.font_hint.render(hint, True, (220, 220, 220))
        hb = pygame.Surface((hs.get_width() + 16, hs.get_height() + 8),
                            pygame.SRCALPHA)
        hb.fill((0, 0, 0, 130))
        self.screen.blit(hb,
                         (8, settings.SCREEN_HEIGHT - hs.get_height() - 16))
        self.screen.blit(hs,
                         (16, settings.SCREEN_HEIGHT - hs.get_height() - 12))

    def _draw_debug(self):
        ts = settings.TILE_SIZE
        tx = int((self.player.x + self.player.w * 0.5) // ts)
        ty = int((self.player.y + self.player.h * 0.5) // ts)
        lines = [
            f"FPS: {self.clock.get_fps():.0f}",
            f"Player: ({self.player.x:.1f}, {self.player.y:.1f})",
            f"Tile:   ({tx}, {ty})",
            f"VX: {self.player.vx:.2f}  VY: {self.player.vy:.2f}  "
            f"Ground: {self.player.on_ground}",
            f"Camera: ({self.camera.x:.0f}, {self.camera.y:.0f})  "
            f"Zoom: {self.camera.zoom:.2f}",
            f"Time: {self.time_of_day:.3f}   Day: {self._day_factor():.2f}",
            f"Sky light: {self._sky_light_level():.2f}",
            f"Flora objects: {len(self.world.flora)}",
            f"Flora sprites: {sum(1 for s in self.flora_sprites if s is not None)}",
            f"Moon phase: {self._moon_phase():.2f}",
        ]
        y = 60
        for line in lines:
            s = self.font_hint.render(line, True, (240, 240, 180))
            bg = pygame.Surface((s.get_width() + 12, s.get_height() + 4),
                                pygame.SRCALPHA)
            bg.fill((0, 0, 0, 150))
            self.screen.blit(bg, (8, y))
            self.screen.blit(s, (14, y + 2))
            y += s.get_height() + 6

    # ------------------------------------------------------------------
    def _draw_loading(self, text):
        self.screen.fill((18, 20, 30))
        font = settings.get_font(32, bold=True)
        surf = font.render(text, True, (200, 210, 240))
        self.screen.blit(surf, surf.get_rect(
            center=(settings.SCREEN_WIDTH // 2,
                    settings.SCREEN_HEIGHT // 2)))
        pygame.display.flip()
        
    def reload_resources(self) -> None:
        """Перезагружает все текстуры (блоки и деревья) на лету."""
        self.tile_surfs = self._load_tile_surfaces()
        self.flora_sprites = self._load_flora_sprites()
        print("[game] Ресурспак обновлён.")

    def _on_keydown(self, event) -> None:
        if event.key == pygame.K_ESCAPE:
            pm = PauseMenu(self.screen, self)
            action = pm.run()
            
            # После выхода из паузы (вдруг там меняли настройки) — обновляем ресурсы
            self.reload_resources()
            
            if action == "menu":
                self.result = "menu"
                self.running = False
            elif action == "quit":
                self.result = "quit"
                self.running = False
            return
        if event.key == pygame.K_F3:
            self.show_debug = not self.show_debug
            return
        if event.key == pygame.K_t:
            if settings.CHEATS_ENABLED:
                self.time_of_day = (self.time_of_day + 1 / 24) % 1.0
            return
        if event.key == pygame.K_F5:
            self.reload_resources()
            return
        