# scripts/texture_gen/params.py
"""Параметры генерации текстуры блока."""
from __future__ import annotations

from dataclasses import dataclass, asdict


_COLOR_KEYS = ("base_color", "vein_color", "crack_color", "speckle_color")


@dataclass
class TextureParams:
    size: int = 16
    base_color: tuple = (110, 70, 40)

    noise_kind: str = "value"
    noise_scale: int = 4
    noise_octaves: int = 2
    noise_intensity: float = 0.4

    dark_shift: float = 0.30
    light_shift: float = 0.30
    hue_shift: float = 0.03
    sat_shift: float = 0.10

    # --- Вены ---
    veins: bool = False
    vein_scale: int = 3               # крупность сети вен
    vein_intensity: float = 0.20      # толщина вен
    vein_color: tuple = (60, 40, 25)

    # --- Трещины ---
    cracks: bool = False
    crack_scale: int = 4              # крупность сети трещин
    crack_intensity: float = 0.12     # толщина трещин
    crack_color: tuple = (60, 60, 70)

    # --- Крапинки ---
    speckles: bool = False
    speckle_scale: int = 3            # размер пятен
    speckle_intensity: float = 0.10   # плотность
    speckle_color: tuple = (150, 120, 80)

    seed: int = 0

    def copy(self) -> "TextureParams":
        return TextureParams.from_dict(asdict(self))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TextureParams":
        d = dict(d)
        for k in _COLOR_KEYS:
            if k in d and isinstance(d[k], list):
                d[k] = tuple(d[k])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
    
    