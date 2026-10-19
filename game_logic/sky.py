# scripts/game_logic/sky.py
"""Слой небесных светил: солнце, луна (с фазами), третье тело.

Каждое светило — своё: цвет, яркость, радиус, время восхода/заката,
высота дуги. Видимость — по времени суток; положение по дуге.
"""
from __future__ import annotations

import math

import pygame


class CelestialBody:
    def __init__(self, name: str, color: tuple, brightness: float,
                 radius: int, rise: float, set_: float,
                 arc_height: float = 0.85, has_phase: bool = False):
        self.name = name
        self.color = color
        self.brightness = brightness      # 0..1
        self.radius = radius
        self.rise = rise                  # 0..1 — доля суток
        self.set = set_
        self.arc_height = arc_height      # высота дуги
        self.has_phase = has_phase

    # ------------------------------------------------------------------
    # Видимость и фаза
    # ------------------------------------------------------------------
    def is_visible(self, t: float) -> bool:
        if self.rise < self.set:
            return self.rise <= t <= self.set
        return t >= self.rise or t <= self.set

    def local_phase(self, t: float) -> float:
        """0 — восход, 1 — закат."""
        if self.rise < self.set:
            return (t - self.rise) / max(1e-6, self.set - self.rise)
        # через полночь
        if t >= self.rise:
            return (t - self.rise) / max(1e-6, (1.0 - self.rise) + self.set)
        return (1.0 - self.rise + t) / max(1e-6, (1.0 - self.rise) + self.set)

    def position(self, t: float, view_w: int, horizon_y: float):
        if not self.is_visible(t):
            return None
        u = self.local_phase(t)
        x = view_w * (0.08 + 0.84 * u)
        arc = math.sin(math.pi * u)
        y = horizon_y - arc * max(20.0, horizon_y) * self.arc_height
        return (x, y)

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, t: float,
             view_w: int, horizon_y: float, moon_phase: float = 0.5) -> None:
        pos = self.position(t, view_w, horizon_y)
        if pos is None:
            return
        x, y = int(pos[0]), int(pos[1])

        if self.has_phase:
            self._draw_moon(surface, x, y, moon_phase)
        else:
            self._draw_sun(surface, x, y)

    def _draw_sun(self, surface, x, y):
        r = self.radius
        # Свечение
        for i in range(3, 0, -1):
            alpha = 45 // i
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*self.color, alpha), (r * 2, r * 2),
                               r + i * 4)
            surface.blit(glow, (x - r * 2, y - r * 2))
        pygame.draw.circle(surface, self.color, (x, y), r)
        light = tuple(min(255, c + 55) for c in self.color)
        pygame.draw.circle(surface, light, (x, y), max(1, r - 3))

    def _draw_moon(self, surface, x, y, phase):
        r = self.radius
        # Рисуем саму луну
        pygame.draw.circle(surface, self.color, (x, y), r)

        # Кратеры
        crater = tuple(max(0, c - 30) for c in self.color)
        for dx, dy, cr in ((-4, -3, 2), (3, -2, 1), (1, 4, 2), (-2, 3, 1)):
            pygame.draw.circle(surface, crater, (x + dx, y + dy), cr)

        # Тень — фаза (рисуем на отдельной поверхности с прозрачностью)
        p = phase % 1.0
        if p <= 0.5:
            offset = p * 4 * r
            shadow_x = int(x - offset)
        else:
            offset = (1 - p) * 4 * r
            shadow_x = int(x + offset)

        if offset < 2 * r:
            shadow_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(shadow_surf, (8, 10, 20, 210), (r + 2, r + 2), r)
            surface.blit(shadow_surf, (shadow_x - r - 2, y - r - 2))
            
class Sky:
    """Контейнер светил + агрегированные значения."""

    def __init__(self):
        self.bodies = [
            # Солнце: ярко, днём
            CelestialBody("Sun", (255, 230, 130), 0.85, 22,
                          rise=0.22, set_=0.78, arc_height=0.85),
            # Луна: тише, ночью, с фазами
            CelestialBody("Moon", (225, 228, 240), 0.15, 16,
                          rise=0.78, set_=0.22, arc_height=0.75,
                          has_phase=True),
            # Третье тело — «красная звезда» на рассвете
            CelestialBody("Ember", (240, 130, 100), 0.06, 8,
                          rise=0.18, set_=0.28, arc_height=0.55),
        ]

    def draw(self, surface, time_of_day, view_w, horizon_y, moon_phase):
        for b in self.bodies:
            b.draw(surface, time_of_day, view_w, horizon_y, moon_phase)

    def extra_light(self, time_of_day) -> float:
        """Вклад светил в суммарную яркость неба (0..1)."""
        total = 0.0
        for b in self.bodies:
            if b.is_visible(time_of_day):
                u = b.local_phase(time_of_day)
                arc = math.sin(math.pi * u)
                total += b.brightness * arc
        return min(1.0, total)
    