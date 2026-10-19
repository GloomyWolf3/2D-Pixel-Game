# scripts/utils/math_utils.py
import math
import random


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def lerp(a, b, t: float):
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def distance(x1, y1, x2, y2) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def random_seed() -> int:
    return random.randint(0, 2**31 - 1)
