# scripts/texture_gen/palette.py
"""HSL-утилиты для сдвига базового цвета."""
from __future__ import annotations

import colorsys


def shift(base_rgb: tuple[int, int, int],
          hue_shift: float = 0.0,
          sat_shift: float = 0.0,
          light_shift: float = 0.0) -> tuple[int, int, int]:
    r, g, b = (c / 255.0 for c in base_rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    h = (h + hue_shift) % 1.0
    s = max(0.0, min(1.0, s + sat_shift))
    l = max(0.0, min(1.0, l + light_shift))

    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))

