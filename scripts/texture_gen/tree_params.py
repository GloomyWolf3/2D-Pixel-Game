# scripts/texture_gen/tree_params.py
"""Параметры генерации дерева/куста (пиксельный стиль)."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class TreeParams:
    size_w: int = 96
    size_h: int = 128

    # ---- Ствол ----
    trunk_w: int = 8
    trunk_h: int = 70
    trunk_taper: float = 0.40
    trunk_color: tuple = (110, 70, 40)
    trunk_dark_shift: float = 0.25
    trunk_light_shift: float = 0.20
    bark_lines: bool = True

    # ---- Ветки ----
    branches: int = 5
    branch_angle: float = 40.0
    branch_len: float = 22.0
    branch_thickness: int = 2

    # ---- Крона ----
    crown_type: str = "round"
    crown_w: int = 76
    crown_h: int = 64
    crown_y_offset: int = -8
    crown_fill: float = 0.9
    crown_holes: float = 0.2
    crown_irregularity: float = 0.3
    leaf_color: tuple = (60, 140, 50)
    leaf_color2: tuple = (90, 170, 70)
    leaf_dark_shift: float = 0.30
    leaf_light_shift: float = 0.30

    leaf_pixel: int = 4
    seed: int = 0

    # ---- Генератор вариаций (Разброс) ----
    variants_count: int = 8
    var_trunk_h: tuple = (50, 90)
    var_crown_w: tuple = (60, 100)
    var_crown_h: tuple = (50, 90)
    var_crown_irregularity: tuple = (0.2, 0.6)
    var_crown_holes: tuple = (0.1, 0.3)

    def copy(self) -> "TreeParams":
        return TreeParams(**asdict(self))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TreeParams":
        d = dict(d)
        # Кортежи из JSON приходят как списки, конвертируем обратно
        tuple_keys = ("trunk_color", "leaf_color", "leaf_color2",
                      "var_trunk_h", "var_crown_w", "var_crown_h",
                      "var_crown_irregularity", "var_crown_holes")
        for k in tuple_keys:
            if k in d and isinstance(d[k], list):
                d[k] = tuple(d[k])
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


PRESETS: dict[str, TreeParams] = {
    "oak": TreeParams(
        size_w=96, size_h=128, trunk_w=8, trunk_h=70, trunk_taper=0.40,
        trunk_color=(110, 70, 40), branches=5, branch_angle=40, branch_len=22,
        branch_thickness=2, crown_type="round", crown_w=80, crown_h=68,
        crown_y_offset=-8, crown_fill=0.90, crown_holes=0.15,
        crown_irregularity=0.35, leaf_color=(60, 140, 50), leaf_color2=(90, 170, 70),
        leaf_pixel=4,
    ),
    "pine": TreeParams(
        size_w=88, size_h=144, trunk_w=6, trunk_h=130, trunk_taper=0.55,
        trunk_color=(90, 60, 40), branches=0, crown_type="cone",
        crown_w=80, crown_h=130, crown_y_offset=-6, crown_fill=0.92,
        crown_holes=0.04, crown_irregularity=0.12,
        leaf_color=(30, 90, 50), leaf_color2=(55, 125, 65), leaf_pixel=4,
        var_crown_w=(70, 90), var_crown_h=(120, 140)
    ),
    "birch": TreeParams(
        size_w=64, size_h=128, trunk_w=5, trunk_h=90, trunk_taper=0.20,
        trunk_color=(230, 225, 210), branches=0, crown_type="narrow",
        crown_w=52, crown_h=76, crown_y_offset=-4, crown_fill=0.85,
        crown_holes=0.22, crown_irregularity=0.42,
        leaf_color=(120, 180, 70), leaf_color2=(160, 210, 90), leaf_pixel=3,
    ),
    "palm": TreeParams(
        size_w=112, size_h=144, trunk_w=6, trunk_h=110, trunk_taper=0.30,
        trunk_color=(140, 100, 60), branches=0, crown_type="palm",
        crown_w=108, crown_h=64, crown_y_offset=-6, crown_fill=0.88,
        crown_holes=0.05, crown_irregularity=0.20,
        leaf_color=(60, 130, 60), leaf_color2=(90, 165, 75), leaf_pixel=4,
    ),
    "bush": TreeParams(
        size_w=48, size_h=48, trunk_w=3, trunk_h=8, trunk_taper=0.0,
        trunk_color=(110, 70, 40), branches=0, crown_type="bush",
        crown_w=46, crown_h=42, crown_y_offset=0, crown_fill=0.95,
        crown_holes=0.08, crown_irregularity=0.30,
        leaf_color=(60, 140, 50), leaf_color2=(90, 170, 70), leaf_pixel=3,
        var_trunk_h=(4, 12)
    ),
}

LABELS = {"oak": "Дуб", "pine": "Ель", "birch": "Берёза", "palm": "Пальма", "bush": "Куст"}
CROWN_TYPES = ["round", "cone", "narrow", "column", "palm", "bush"]
CROWN_LABELS = {"round": "Круглая", "cone": "Конус", "narrow": "Узкая", "column": "Колонна", "palm": "Пальма", "bush": "Куст"}
