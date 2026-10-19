# scripts/game_logic/lighting.py
"""Освещение.

Использует предрассчитанный sky_mask (карту проникновения неба) —
никакого BFS в кадре. Плюс круглый источник света вокруг игрока.
"""
from __future__ import annotations

import numpy as np

from scripts.game_logic import tiles as T


_SOLID_ARRAY_CACHE: dict[str, np.ndarray] = {}


def _is_solid_array() -> np.ndarray:
    if "v" not in _SOLID_ARRAY_CACHE:
        arr = np.zeros(256, dtype=bool)
        for t in T.SOLID:
            arr[t] = True
        _SOLID_ARRAY_CACHE["v"] = arr
    return _SOLID_ARRAY_CACHE["v"]


def compute_light_map(tiles: np.ndarray,
                      sky_mask: np.ndarray,
                      sky_level: float,
                      player_x: float, player_y: float,
                      player_radius: float = 13.0,
                      player_brightness: float = 1.0) -> np.ndarray:
    """tiles:     (vw, vh) uint8 — срез тайлов.
    sky_mask:  (vw, vh) bool  — тот же срез карты неба.
    sky_level: 0..1 — насколько сейчас светло снаружи.

    Возвращает float32 (vw, vh) со значением света 0..1.
    """
    vw, vh = tiles.shape
    light = np.zeros((vw, vh), dtype=np.float32)

    # ---------------- Небо ----------------
    if sky_level > 0.001:
        light[sky_mask] = sky_level

        # Твёрдые тайлы, соседствующие с освещённым воздухом, получают
        # подсветку сверху (60% от sky_level).
        solid = _is_solid_array()[tiles]
        exp = sky_mask.copy()
        exp[:-1, :] |= sky_mask[1:, :]
        exp[1:, :]  |= sky_mask[:-1, :]
        exp[:, :-1] |= sky_mask[:, 1:]
        exp[:, 1:]  |= sky_mask[:, :-1]
        partial = exp & solid & ~sky_mask
        np.maximum(light, np.where(partial, sky_level * 0.6, 0.0),
                   out=light)

    # ---------------- Свет игрока: ровный круг ----------------
    if player_radius > 0:
        xs = np.arange(vw, dtype=np.float32)[:, None]   # (vw, 1)
        ys = np.arange(vh, dtype=np.float32)[None, :]   # (1, vh)
        dx = xs - player_x
        dy = ys - player_y
        dist2 = dx * dx + dy * dy
        r2 = player_radius * player_radius
        pl = np.clip(1.0 - dist2 / r2, 0.0, 1.0)
        pl = pl * pl * player_brightness
        np.maximum(light, pl, out=light)

    return np.clip(light, 0.0, 1.0)

