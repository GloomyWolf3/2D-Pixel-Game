# scripts/world_gen/cave_gen.py
"""Генерация пещер «червями» (worm-based carving).

Несколько червей блуждают под поверхностью и «выгрызают» круглые полости.
Приповерхностный слой (первые ~4 тайла под землёй) не трогается,
чтобы не дырявить небо.
"""
from __future__ import annotations

import numpy as np


def generate_caves(seed: int, width: int, height: int,
                   surface_y: np.ndarray,
                   num_worms: int = 45) -> np.ndarray:
    """Возвращает bool-массив формы (width, height): True = пещера."""
    rng = np.random.default_rng(seed + 999_331)
    caves = np.zeros((width, height), dtype=bool)

    # Предрассчитываем «можно копать»: строго ниже surface_y + 4
    y_grid = np.arange(height, dtype=np.int64)[None, :]     # (1, h)
    sy_col = surface_y[:, None]                              # (w, 1)
    below_surface = y_grid > (sy_col + 4)                    # (w, h)

    for _ in range(num_worms):
        start_x = float(rng.uniform(5, width - 6))
        sx = int(start_x)
        top = int(surface_y[sx]) + 30
        if top >= height - 20:
            continue

        x = start_x
        y = float(rng.uniform(top, height - 10))
        angle = float(rng.uniform(0.0, 2.0 * np.pi))
        steps = int(rng.integers(150, 420))
        base_radius = float(rng.uniform(1.6, 3.6))

        for _s in range(steps):
            xi, yi = int(x), int(y)
            r = int(np.ceil(base_radius))

            # Границы области с клипом по миру
            x0 = max(0, xi - r)
            x1 = min(width, xi + r + 1)
            y0 = max(0, yi - r)
            y1 = min(height, yi + r + 1)

            if x0 >= x1 or y0 >= y1:
                break

            # Локальные смещения и круглая маска на обрезанной сетке
            xs = np.arange(x0, x1, dtype=np.int64)
            ys = np.arange(y0, y1, dtype=np.int64)
            gx = (xs - xi)[:, None]          # (nx, 1)
            gy = (ys - yi)[None, :]          # (1, ny)
            circle = (gx * gx + gy * gy) <= (base_radius * base_radius)
            # circle.shape == (x1 - x0, y1 - y0)

            region = below_surface[x0:x1, y0:y1]
            # region.shape == (x1 - x0, y1 - y0) — совпадает с circle

            caves[x0:x1, y0:y1] |= (circle & region)

            # Шаг червя
            angle += float(rng.uniform(-0.35, 0.35))
            x += float(np.cos(angle)) * 1.6
            y += float(np.sin(angle)) * 1.6

            # Клип внутри мира
            x = float(np.clip(x, 5, width - 6))
            sy_local = int(surface_y[int(x)])
            y = float(np.clip(y, sy_local + 6, height - 5))

    return caves

