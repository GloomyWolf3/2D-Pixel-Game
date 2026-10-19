# scripts/world_gen/terrain_gen.py
"""Генерация рельефа поверхности.

Два режима шума:
  * "value"        — многооктавный value-noise (быстрый, «блочный»).
  * "opensimplex"  — OpenSimplex (плавный, «органичный»).
"""
from __future__ import annotations

import numpy as np


def _value_noise_1d(rng: np.random.Generator, width: int,
                    base_period: float, octaves: int) -> np.ndarray:
    result = np.zeros(width, dtype=np.float64)
    amplitude = 1.0
    total_amp = 0.0

    for octave in range(octaves):
        period = base_period / (2 ** octave)
        n_points = max(3, int(width / period) + 2)
        control = rng.uniform(-1.0, 1.0, n_points)

        x = np.linspace(0, n_points - 1, width)
        x0 = np.floor(x).astype(np.int64)
        x1 = np.minimum(x0 + 1, n_points - 1)
        t = x - x0
        t = t * t * (3.0 - 2.0 * t)

        result += (control[x0] * (1.0 - t) + control[x1] * t) * amplitude
        total_amp += amplitude
        amplitude *= 0.5

    return result / total_amp


def generate_heightmap(seed: int, width: int, height: int,
                       noise_kind: str = "value") -> np.ndarray:
    """Возвращает массив высот поверхности формы (width,)."""
    rng = np.random.default_rng(seed)

    if noise_kind == "opensimplex":
        try:
            from scripts.world_gen.opensimplex_noise import opensimplex_1d
            noise = opensimplex_1d(seed, width, base_freq=0.004, octaves=6)
        except ImportError:
            noise = _value_noise_1d(rng, width, base_period=420.0, octaves=6)
    else:
        noise = _value_noise_1d(rng, width, base_period=420.0, octaves=6)

    ground_min = int(height * 0.32)
    ground_max = int(height * 0.62)
    span = ground_max - ground_min

    surface = (ground_min + (noise + 1.0) * 0.5 * span).astype(np.int64)
    surface = np.clip(surface, 8, height - 40)
    return surface


# Экспорт для biome_gen — чтобы не дублировать код
def value_noise_1d(rng: np.random.Generator, width: int,
                   base_period: float, octaves: int) -> np.ndarray:
    return _value_noise_1d(rng, width, base_period, octaves)

