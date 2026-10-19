# scripts/world_gen/flora_gen.py
from __future__ import annotations
import numpy as np
from scripts.config import settings
from scripts.game_logic import tiles as T
from scripts.texture_gen.tree_params import PRESETS
from scripts.world_gen.biome_gen import (
    BIOME_PLAINS, BIOME_FOREST, BIOME_DESERT, BIOME_SNOW,
)

BIOME_FLORA = {
    BIOME_FOREST: (0.30, ["oak", "oak", "oak", "birch"], 0.18),
    BIOME_PLAINS: (0.08, ["oak"],                        0.12),
    BIOME_SNOW:   (0.26, ["pine"],                       0.14),
    BIOME_DESERT: (0.12, ["palm"],                       0.04),
}

# Индивидуальный масштаб для каждого типа (относительно базового спрайта)
# 2.0 означает, что дерево будет в 2 раза больше нарисованного в редакторе
BASE_SCALES = {
    "oak": 2.5,
    "pine": 2.5,
    "birch": 2.0,
    "palm": 2.5,
    "bush": 0.8, # Кусты делаем маленькими!
}

_VALID_TOPS = (T.GRASS, T.SAND, T.SNOW, T.DIRT, T.SANDSTONE)

def _find_top(world, tx: int, sy: int) -> int | None:
    for probe in (0, -1, 1, -2, 2, -3, 3):
        py = sy + probe
        if 0 <= py < world.height:
            t = int(world.tiles[tx, py])
            if t in _VALID_TOPS:
                return py
    return None

def generate_flora(world) -> list[dict]:
    rng = np.random.default_rng(world.seed + 4242)
    flora: list[dict] = []

    next_spawn_tx = 0

    for tx in range(world.width):
        if tx < next_spawn_tx:
            continue

        biome = int(world.biomes[tx])
        p_tree, kinds, p_bush = BIOME_FLORA.get(biome, (0.0, [], 0.0))
        if not kinds and p_bush <= 0.0:
            continue

        sy = int(world.surface_y[tx])
        if not (0 <= sy < world.height):
            continue

        top_y = _find_top(world, tx, sy)
        if top_y is None:
            continue

        roll = float(rng.random())
        
        if roll < p_tree:
            kind = kinds[int(rng.integers(0, len(kinds)))]
            base_scale = BASE_SCALES.get(kind, 2.0)
            # Небольшой рандом +-15%
            scale = base_scale * float(rng.uniform(0.85, 1.15))
            
            base_w = PRESETS[kind].crown_w if kind in PRESETS else 80
            width_tiles = (base_w * scale) / settings.TILE_SIZE
            gap_tiles = rng.uniform(1.0, 2.5) * width_tiles
            next_spawn_tx = tx + int(gap_tiles)

            flora.append({
                "kind": str(kind), "tx": tx, "ty": top_y, "scale": scale,
                "flip": bool(rng.random() < 0.5), "seed": int(rng.integers(0, 2**31 - 1)),
            })
            
        elif roll < p_tree + p_bush:
            base_scale = BASE_SCALES["bush"]
            scale = base_scale * float(rng.uniform(0.85, 1.15))
            
            base_w = PRESETS["bush"].crown_w if "bush" in PRESETS else 46
            width_tiles = (base_w * scale) / settings.TILE_SIZE
            
            # Кусты сажаем плотнее, но не впритык
            gap_tiles = rng.uniform(0.5, 1.5) * width_tiles
            next_spawn_tx = tx + int(gap_tiles)
            
            flora.append({
                "kind": "bush", "tx": tx, "ty": top_y, "scale": scale,
                "flip": bool(rng.random() < 0.5), "seed": int(rng.integers(0, 2**31 - 1)),
            })

    flora.sort(key=lambda f: (f["ty"], f["tx"]))
    print(f"[flora_gen] placed: {len(flora)} objects (seed={world.seed})")
    return flora
