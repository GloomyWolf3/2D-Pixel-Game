# scripts/world_gen/biome_gen.py
"""Разбиение мира по X на биомы с плавными переходами."""
from __future__ import annotations

import numpy as np

from scripts.world_gen.terrain_gen import value_noise_1d


BIOME_PLAINS = 0
BIOME_FOREST = 1
BIOME_DESERT = 2
BIOME_SNOW   = 3

BIOME_NAMES = {
    BIOME_PLAINS: "Равнины",
    BIOME_FOREST: "Лес",
    BIOME_DESERT: "Пустыня",
    BIOME_SNOW:   "Снежные земли",
}


def generate_biomes(seed: int, width: int, height: int,
                    noise_kind: str = "value") -> np.ndarray:
    rng = np.random.default_rng(seed + 12345)

    if noise_kind == "opensimplex":
        try:
            from scripts.world_gen.opensimplex_noise import opensimplex_1d
            temp = opensimplex_1d(seed + 777, width, base_freq=0.002, octaves=3)
        except ImportError:
            temp = value_noise_1d(rng, width, base_period=900.0, octaves=3)
    else:
        temp = value_noise_1d(rng, width, base_period=900.0, octaves=3)

    temp01 = (temp + 1.0) * 0.5
    biomes = np.empty(width, dtype=np.int8)
    biomes[temp01 < 0.20] = BIOME_DESERT
    biomes[(temp01 >= 0.20) & (temp01 < 0.45)] = BIOME_PLAINS
    biomes[(temp01 >= 0.45) & (temp01 < 0.78)] = BIOME_FOREST
    biomes[temp01 >= 0.78] = BIOME_SNOW
    return biomes
