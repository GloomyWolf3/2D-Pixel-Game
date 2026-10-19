# scripts/texture_gen/noise.py
"""Шумовые функции для генерации текстур (numpy, векторно)."""
from __future__ import annotations

import numpy as np


def _grid_sample(grid: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Билинейная выборка квадратной сетки grid[n, n] в координатах xs, ys."""
    n = grid.shape[0]
    x0 = np.clip(np.floor(xs).astype(np.int32), 0, n - 1)
    y0 = np.clip(np.floor(ys).astype(np.int32), 0, n - 1)
    x1 = np.minimum(x0 + 1, n - 1)
    y1 = np.minimum(y0 + 1, n - 1)

    tx = xs - x0
    ty = ys - y0
    tx = tx * tx * (3.0 - 2.0 * tx)
    ty = ty * ty * (3.0 - 2.0 * ty)

    v00 = grid[y0[:, None], x0[None, :]]
    v01 = grid[y0[:, None], x1[None, :]]
    v10 = grid[y1[:, None], x0[None, :]]
    v11 = grid[y1[:, None], x1[None, :]]

    top = v00 * (1.0 - tx)[None, :] + v01 * tx[None, :]
    bot = v10 * (1.0 - tx)[None, :] + v11 * tx[None, :]
    return top * (1.0 - ty)[:, None] + bot * ty[:, None]


def value_noise(rng: np.random.Generator, size: int,
                scale: int, octaves: int = 1) -> np.ndarray:
    result = np.zeros((size, size), dtype=np.float32)
    amp = 1.0
    total = 0.0
    for octave in range(max(1, octaves)):
        period = max(2, int(scale / (2 ** octave)))
        n = max(2, size // period + 2)
        grid = rng.random((n, n), dtype=np.float32)
        coords = np.linspace(0, n - 1, size, dtype=np.float32)
        result += _grid_sample(grid, coords, coords) * amp
        total += amp
        amp *= 0.5
    return result / total


def worley_noise(rng: np.random.Generator, size: int,
                 cells: int) -> np.ndarray:
    n = max(1, cells)
    pts = rng.random((n * n, 2), dtype=np.float32) * size
    yy, xx = np.mgrid[0:size, 0:size]
    coords = np.stack([xx.ravel(), yy.ravel()], axis=1).astype(np.float32)

    diff = coords[:, None, :] - pts[None, :, :]
    dist = np.sqrt((diff * diff).sum(axis=2))
    f1 = dist.min(axis=1).reshape(size, size)

    # нормализуем примерно в 0..1 (среднее расстояние между точками ~ size/n)
    f1 = f1 / max(1e-3, (size / n))
    return np.clip(f1, 0.0, 1.0)


def white_noise(rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.random((size, size), dtype=np.float32)


