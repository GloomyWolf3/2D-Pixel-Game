# scripts/world_gen/background_gen.py
"""Цвета фона по биомам + прекомпьют со сглаживанием границ."""
from __future__ import annotations

import numpy as np

from scripts.world_gen.biome_gen import (
    BIOME_PLAINS, BIOME_FOREST, BIOME_DESERT, BIOME_SNOW,
)


BG_SURFACE = {
    BIOME_PLAINS: (135, 180, 115),
    BIOME_FOREST: (95, 140, 85),
    BIOME_DESERT: (215, 185, 130),
    BIOME_SNOW:   (200, 218, 235),
}

BG_DEEP = {
    BIOME_PLAINS: (34, 38, 48),
    BIOME_FOREST: (30, 34, 44),
    BIOME_DESERT: (52, 44, 38),
    BIOME_SNOW:   (48, 54, 68),
}


def _gauss_kernel(sigma: float, half: int) -> np.ndarray:
    x = np.arange(-half, half + 1, dtype=np.float32)
    k = np.exp(-(x * x) / (2.0 * sigma * sigma))
    k /= k.sum()
    return k


def precompute(world) -> tuple[np.ndarray, np.ndarray]:
    """Возвращает (bg_top, bg_bot) — массивы формы (width, 3) uint8.

    Цвета сглажены по X, чтобы переходы между биомами были плавными.
    """
    w = world.width
    top = np.zeros((w, 3), dtype=np.float32)
    bot = np.zeros((w, 3), dtype=np.float32)

    for tx in range(w):
        biome = int(world.biomes[tx])
        top[tx] = BG_SURFACE.get(biome, (100, 100, 120))
        bot[tx] = BG_DEEP.get(biome, (40, 40, 50))

    # Сглаживание по X (гаусс, ~80 тайлов в стороны)
    kernel = _gauss_kernel(sigma=28.0, half=80)

    for c in range(3):
        top[:, c] = np.convolve(top[:, c], kernel, mode="same")
        bot[:, c] = np.convolve(bot[:, c], kernel, mode="same")

    return (np.clip(top, 0, 255).astype(np.uint8),
            np.clip(bot, 0, 255).astype(np.uint8))

