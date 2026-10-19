from scripts.game_logic.player import Player
from scripts.game_logic.entities import Entity
from scripts.world_gen.terrain_gen import generate_terrain
from scripts.world_gen.cave_gen import generate_caves
from scripts.world_gen.biome_gen import generate_biomes

def initialize_game():
    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    terrain = generate_terrain(WORLD_SIZE)
    caves = generate_caves(WORLD_SIZE)
    biomes = generate_biomes(WORLD_SIZE)

    return player, terrain, caves, biomes
