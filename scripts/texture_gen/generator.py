# scripts/texture_gen/generator.py
"""Сборка текстуры из параметров: шум → палитра → узоры."""
from __future__ import annotations

import numpy as np
import pygame

from scripts.texture_gen import noise as N
from scripts.texture_gen.palette import shift
from scripts.texture_gen.params import TextureParams


def generate_rgb(params: TextureParams) -> np.ndarray:
    size = params.size
    rng = np.random.default_rng(params.seed)

    # --- 1. Базовый шум ---
    if params.noise_kind == "worley":
        n = N.worley_noise(rng, size, params.noise_scale)
    elif params.noise_kind == "white":
        n = N.white_noise(rng, size)
    else:
        n = N.value_noise(rng, size, params.noise_scale, params.noise_octaves)

    t = 0.5 + (np.clip(n, 0.0, 1.0) - 0.5) * (params.noise_intensity * 2.0)
    t = np.clip(t, 0.0, 1.0)

    base = params.base_color
    dark = np.array(shift(base, -params.hue_shift, -params.sat_shift,
                          -params.dark_shift), dtype=np.float32)
    light = np.array(shift(base, params.hue_shift, params.sat_shift,
                           params.light_shift), dtype=np.float32)

    rgb = (dark[None, None, :] * (1.0 - t)[:, :, None]
           + light[None, None, :] * t[:, :, None])

    # --- 2. Вены ---
    if params.veins:
        v = N.value_noise(rng, size, max(2, params.vein_scale), 1)
        dist = np.abs(v - 0.5) * 2.0
        thickness = max(0.02, params.vein_intensity)
        mask = np.clip(1.0 - dist / thickness, 0.0, 1.0)
        vc = np.array(params.vein_color, dtype=np.float32)
        rgb = (rgb * (1.0 - mask)[:, :, None]
               + vc[None, None, :] * mask[:, :, None])

    # --- 3. Трещины (та же логика, но тоньше и другим цветом) ---
    if params.cracks:
        c = N.value_noise(rng, size, max(2, params.crack_scale), 1)
        dist = np.abs(c - 0.5) * 2.0
        thickness = max(0.02, params.crack_intensity)
        mask = np.clip(1.0 - dist / thickness, 0.0, 1.0)
        cc = np.array(params.crack_color, dtype=np.float32)
        rgb = (rgb * (1.0 - mask)[:, :, None]
               + cc[None, None, :] * mask[:, :, None])

    # --- 4. Крапинки (бинаризация мелкого шума) ---
    if params.speckles:
        s = N.value_noise(rng, size, max(2, params.speckle_scale), 1)
        density = max(0.01, params.speckle_intensity)
        mask = (s < density).astype(np.float32)
        sc = np.array(params.speckle_color, dtype=np.float32)
        rgb = (rgb * (1.0 - mask)[:, :, None]
               + sc[None, None, :] * mask[:, :, None])

    return np.clip(rgb, 0, 255).astype(np.uint8)

def generate_surface(params: TextureParams) -> pygame.Surface:
    arr = generate_rgb(params)
    surf = pygame.Surface((params.size, params.size))
    px = pygame.surfarray.pixels3d(surf)
    px[:] = arr
    del px
    return surf


