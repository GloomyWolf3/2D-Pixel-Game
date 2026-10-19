# scripts/game_logic/player.py
"""Игрок: движение, прыжок, коллизии с тайлами."""
from __future__ import annotations

import pygame

from scripts.config import settings
from scripts.game_logic import tiles as T


class Player:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.w = 12
        self.h = 24

        self.speed = 4.2
        self.jump_velocity = -8.6
        self.gravity = 0.5
        self.max_fall = 18.0

        self.on_ground = False

    # ------------------------------------------------------------------
    # Ввод / физика
    # ------------------------------------------------------------------
    def update(self, world, keys, dt: float) -> None:
        ax = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            ax -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            ax += 1
        self.vx = ax * self.speed

        jump_pressed = (keys[pygame.K_SPACE]
                        or keys[pygame.K_w]
                        or keys[pygame.K_UP])
        if jump_pressed and self.on_ground:
            self.vy = self.jump_velocity
            self.on_ground = False

        self.vy = min(self.vy + self.gravity, self.max_fall)

        # X
        new_x = self.x + self.vx
        if not self._collides(world, new_x, self.y):
            self.x = new_x

        # Y
        new_y = self.y + self.vy
        if not self._collides(world, self.x, new_y):
            self.y = new_y
            self.on_ground = False
        else:
            if self.vy > 0:
                self.on_ground = True
            self.vy = 0.0

    def _collides(self, world, x: float, y: float) -> bool:
        ts = settings.TILE_SIZE
        x0 = int(x // ts)
        x1 = int((x + self.w - 1) // ts)
        y0 = int(y // ts)
        y1 = int((y + self.h - 1) // ts)

        if x0 < 0 or x1 >= world.width or y0 < 0 or y1 >= world.height:
            return True

        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if world.get_tile(tx, ty) in T.SOLID:
                    return True
        return False

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface,
             cam_x: float, cam_y: float) -> None:
        sx = self.x - cam_x
        sy = self.y - cam_y
        rect = pygame.Rect(int(sx), int(sy), self.w, self.h)
        pygame.draw.rect(surface, (240, 200, 160), rect, border_radius=2)
        # «лицо» — направление взгляда
        eye_x = rect.right - 4 if self.vx >= 0 else rect.left + 1
        pygame.draw.rect(surface, (30, 30, 40),
                         (eye_x, rect.top + 5, 3, 3))
        
        