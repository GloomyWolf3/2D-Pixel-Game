# scripts/game_logic/world.py
"""Тайловая карта мира + генерация + кэш + карта неба + растительность."""
from __future__ import annotations

import os
from collections import deque

import numpy as np

from scripts.config import settings
from scripts.game_logic import tiles as T
from scripts.world_gen import (
    terrain_gen, biome_gen, cave_gen, flora_gen, background_gen,
)
from scripts.world_gen.biome_gen import (
    BIOME_PLAINS, BIOME_FOREST, BIOME_DESERT, BIOME_SNOW,
)


_TOP_BY_BIOME = {
    BIOME_PLAINS: T.GRASS,
    BIOME_FOREST: T.GRASS,
    BIOME_DESERT: T.SAND,
    BIOME_SNOW:   T.SNOW,
}
_SUB_BY_BIOME = {
    BIOME_PLAINS: T.DIRT,
    BIOME_FOREST: T.DIRT,
    BIOME_DESERT: T.SANDSTONE,
    BIOME_SNOW:   T.DIRT,
}


class World:
    def __init__(self, seed: int, size: str,
                 save_folder: str | None = None,
                 noise_kind: str = "value"):
        self.seed = seed
        self.size = size
        self.noise_kind = noise_kind
        self.width, self.height = settings.WORLD_SIZES[size]
        self.save_folder = save_folder

        # дефолты, чтобы ничего не падало, если что-то пойдёт не так
        self.flora: list[dict] = []
        self.bg_top = np.zeros((self.width, 3), dtype=np.uint8)
        self.bg_bot = np.zeros((self.width, 3), dtype=np.uint8)

        cache = self._cache_path()
        if cache and os.path.isfile(cache):
            self._load(cache)
        else:
            self._generate()
            if cache:
                self._save(cache)

    # ------------------------------------------------------------------
    # Кэш
    # ------------------------------------------------------------------
    def _cache_path(self) -> str | None:
        if not self.save_folder:
            return None
        return os.path.join(settings.SAVES_DIR, self.save_folder, "world.npz")

    def _save(self, path: str) -> None:
        np.savez_compressed(
            path,
            tiles=self.tiles,
            surface_y=self.surface_y,
            biomes=self.biomes,
            sky_mask=self.sky_mask,
            sea_level=np.array([self.sea_level], dtype=np.int32),
        )

    def save(self) -> None:
        """Публичный метод — сохранить мир на диск."""
        cache = self._cache_path()
        if cache:
            self._save(cache)

    def _load(self, path: str) -> None:
        data = np.load(path)
        self.tiles = data["tiles"]
        self.surface_y = data["surface_y"]
        self.biomes = data["biomes"]
        self.sea_level = int(data["sea_level"][0])
        if "sky_mask" in data:
            self.sky_mask = data["sky_mask"]
        else:
            self.sky_mask = self._compute_sky_mask()

        # Flora регенерируется детерминированно из сида
        self.flora = flora_gen.generate_flora(self)
        self.bg_top, self.bg_bot = background_gen.precompute(self)

    # ------------------------------------------------------------------
    # Генерация
    # ------------------------------------------------------------------
    def _generate(self) -> None:
        self.surface_y = terrain_gen.generate_heightmap(
            self.seed, self.width, self.height,
            noise_kind=self.noise_kind)
        self.biomes = biome_gen.generate_biomes(
            self.seed, self.width, self.height,
            noise_kind=self.noise_kind)

        self.tiles = self._build_tiles()

        caves = cave_gen.generate_caves(
            self.seed, self.width, self.height, self.surface_y,
            num_worms=max(20, self.width // 60),
        )
        self.tiles[caves] = T.AIR

        self.sea_level = int(self.height * 0.55)
        self._apply_water()

        self.sky_mask = self._compute_sky_mask()
        self.flora = flora_gen.generate_flora(self)
        self.bg_top, self.bg_bot = background_gen.precompute(self)

    def _build_tiles(self) -> np.ndarray:
        w, h = self.width, self.height
        tiles = np.full((w, h), T.STONE, dtype=np.uint8)

        y_idx = np.arange(h, dtype=np.int64)[None, :]
        sy = self.surface_y[:, None]

        tiles[y_idx < sy] = T.AIR

        sub_mask = (y_idx >= sy) & (y_idx < sy + 5)
        tiles[sub_mask] = T.DIRT

        for biome_id in np.unique(self.biomes):
            bx = (self.biomes == biome_id)[:, None]
            top = _TOP_BY_BIOME.get(int(biome_id), T.GRASS)
            sub = _SUB_BY_BIOME.get(int(biome_id), T.DIRT)

            tiles[bx & (y_idx == sy)] = top
            tiles[bx & (y_idx < sy + 5) & (y_idx >= sy)] = sub

        tiles[:, h - 2:] = T.BEDROCK
        return tiles

    def _apply_water(self) -> None:
        w = self.width
        for x in range(w):
            sy = int(self.surface_y[x])
            if sy > self.sea_level:
                self.tiles[x, self.sea_level:sy] = T.WATER

    # ------------------------------------------------------------------
    # Sky mask
    # ------------------------------------------------------------------
    def _compute_sky_mask(self) -> np.ndarray:
        w, h = self.width, self.height
        solid = np.zeros((w, h), dtype=bool)
        for t in T.SOLID:
            solid |= (self.tiles == t)

        mask = np.zeros((w, h), dtype=bool)
        dq: deque[tuple[int, int]] = deque()

        for x in range(w):
            if not solid[x, 0]:
                mask[x, 0] = True
                dq.append((x, 0))

        while dq:
            x, y = dq.popleft()
            if x > 0 and not mask[x - 1, y] and not solid[x - 1, y]:
                mask[x - 1, y] = True
                dq.append((x - 1, y))
            if x + 1 < w and not mask[x + 1, y] and not solid[x + 1, y]:
                mask[x + 1, y] = True
                dq.append((x + 1, y))
            if y > 0 and not mask[x, y - 1] and not solid[x, y - 1]:
                mask[x, y - 1] = True
                dq.append((x, y - 1))
            if y + 1 < h and not mask[x, y + 1] and not solid[x, y + 1]:
                mask[x, y + 1] = True
                dq.append((x, y + 1))

        return mask

    def _update_sky_mask_local(self, tx: int, ty: int) -> None:
        w, h = self.width, self.height
        if not (0 <= tx < w and 0 <= ty < h):
            return
        if self.sky_mask[tx, ty]:
            return

        reachable = (ty == 0)
        for nx, ny in ((tx - 1, ty), (tx + 1, ty),
                       (tx, ty - 1), (tx, ty + 1)):
            if 0 <= nx < w and 0 <= ny < h and self.sky_mask[nx, ny]:
                reachable = True
                break
        if not reachable:
            return

        solid_lut = np.zeros(256, dtype=bool)
        for t in T.SOLID:
            solid_lut[t] = True

        dq: deque[tuple[int, int]] = deque([(tx, ty)])
        self.sky_mask[tx, ty] = True

        while dq:
            x, y = dq.popleft()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < w and 0 <= ny < h and not self.sky_mask[nx, ny]:
                    if not solid_lut[self.tiles[nx, ny]]:
                        self.sky_mask[nx, ny] = True
                        dq.append((nx, ny))

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def get_tile(self, tx: int, ty: int) -> int:
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return int(self.tiles[tx, ty])
        return T.AIR

    def set_tile(self, tx: int, ty: int, tile_id: int) -> None:
        if not (0 <= tx < self.width and 0 <= ty < self.height):
            return
        prev = int(self.tiles[tx, ty])
        self.tiles[tx, ty] = tile_id
        if prev != T.AIR and tile_id == T.AIR:
            self._update_sky_mask_local(tx, ty)

    def biome_at(self, tx: int) -> int:
        if 0 <= tx < self.width:
            return int(self.biomes[tx])
        return BIOME_PLAINS
    