# scripts/world_gen/opensimplex_noise.py
"""Обёртка над opensimplex с поддержкой разных версий API.

Совместимо с:
  * opensimplex >= 0.4  (методы noise2 / noise3, конструктор seed=...)
  * opensimplex < 0.4   (методы noise2d / noise3d)
  * отсутствием библиотеки (импорт пройдёт, но функция кинет ImportError)
"""
from __future__ import annotations

import numpy as np

try:
    from opensimplex import OpenSimplex
    HAVE_OPENSIMPLEX = True
except ImportError:
    HAVE_OPENSIMPLEX = False


def _make_gen(seed: int):
    """Создаёт OpenSimplex-генератор, подстраиваясь под версию API."""
    # Попытка 1: современный конструктор (0.4+)
    try:
        return OpenSimplex(seed=seed)
    except TypeError:
        pass
    # Попытка 2: старый конструктор (позиционный)
    return OpenSimplex(seed)


def _noise2(gen, x: float, y: float) -> float:
    """Универсальный вызов 2D-шума."""
    fn = getattr(gen, "noise2", None)
    if fn is None:
        fn = getattr(gen, "noise2d", None)
    if fn is None:
        raise AttributeError("OpenSimplex: не найден метод noise2/noise2d")
    return fn(x, y)


def opensimplex_1d(seed: int, width: int, base_freq: float,
                   octaves: int = 6) -> np.ndarray:
    """Fractal 1D OpenSimplex шум.

    Возвращает массив (width,), нормированный примерно в диапазон -1..1.
    Бросает ImportError, если библиотека не установлена.
    """
    if not HAVE_OPENSIMPLEX:
        raise ImportError("opensimplex не установлен")

    gen = _make_gen(seed)

    out = np.zeros(width, dtype=np.float64)
    amp = 1.0
    total = 0.0

    # Мы считаем «1D» через 2D: y = 0. Это стандартный приём.
    for o in range(octaves):
        freq = base_freq * (2 ** o)
        for x in range(width):
            out[x] += _noise2(gen, x * freq, 0.0) * amp
        total += amp
        amp *= 0.5

    out /= total

    # Нормализация в -1..1 через 1-й / 99-й перцентили
    lo, hi = np.percentile(out, [1.0, 99.0])
    span = max(1e-6, hi - lo)
    out = (out - lo) / span * 2.0 - 1.0
    return np.clip(out, -1.0, 1.0)

