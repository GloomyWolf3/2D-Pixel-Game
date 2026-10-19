# scripts/game_logic/tiles.py
"""Идентификаторы тайлов и их свойства."""

AIR = 0
DIRT = 1
GRASS = 2
STONE = 3
SAND = 4
WATER = 5
SANDSTONE = 6
SNOW = 7
ICE = 8
BEDROCK = 9

SOLID = {DIRT, GRASS, STONE, SAND, SANDSTONE, SNOW, ICE, BEDROCK}
LIQUID = {WATER}

TILE_COLORS = {
    DIRT:      (110, 70, 40),
    GRASS:     (70, 140, 60),
    STONE:     (100, 100, 110),
    SAND:      (222, 202, 132),
    WATER:     (58, 108, 198),
    SANDSTONE: (198, 158, 88),
    SNOW:      (232, 236, 246),
    ICE:       (150, 200, 230),
    BEDROCK:   (28, 28, 34),
}


