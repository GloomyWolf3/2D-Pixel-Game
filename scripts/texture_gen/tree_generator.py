# scripts/texture_gen/tree_generator.py
"""Процедурная генерация дерева/куста в пиксельном стиле."""
from __future__ import annotations

import numpy as np
import pygame

from scripts.texture_gen.tree_params import TreeParams


def generate_tree_rgb(params: TreeParams) -> np.ndarray:
    W, H = params.size_w, params.size_h
    rng = np.random.default_rng(params.seed)
    img = np.zeros((H, W, 4), dtype=np.uint8)

    cx = W // 2
    base_y = H - 1
    trunk_top_y = max(2, base_y - params.trunk_h)

    trunk_mask = _trunk_mask(params, W, H, cx, trunk_top_y, base_y, rng)
    trunk_rgb = _colorize_trunk(trunk_mask, params, rng)
    img[trunk_mask, :3] = trunk_rgb[trunk_mask]
    img[trunk_mask, 3] = 255

    crown_cx = cx
    crown_cy = trunk_top_y + params.crown_y_offset + params.crown_h // 2

    crown_mask, leaf_idx = _generate_crown(
        params, W, H, crown_cx, crown_cy, rng)

    crown_mask[base_y - 2:base_y + 1, :] = False

    if crown_mask.any():
        palette = _leaf_palette(params)
        img[crown_mask, :3] = palette[leaf_idx[crown_mask]]
        img[crown_mask, 3] = 255

    return img


def generate_tree_surface(params: TreeParams) -> pygame.Surface:
    arr = generate_tree_rgb(params)
    surf = pygame.Surface((params.size_w, params.size_h), pygame.SRCALPHA)

    rgb = pygame.surfarray.pixels3d(surf)
    rgb[:, :, :] = np.transpose(arr[:, :, :3], (1, 0, 2))
    del rgb

    alpha = pygame.surfarray.pixels_alpha(surf)
    alpha[:, :] = np.transpose(arr[:, :, 3], (1, 0))
    del alpha

    return surf


def _trunk_mask(params, W, H, cx, trunk_top_y, base_y, rng):
    mask = np.zeros((H, W), dtype=bool)

    for y in range(trunk_top_y, base_y + 1):
        t = (y - trunk_top_y) / max(1, params.trunk_h)
        w_now = max(1.0, params.trunk_w *
                    (1.0 - params.trunk_taper * (1.0 - t)))
        half = w_now * 0.5
        x0 = max(0, int(round(cx - half)))
        x1 = min(W, int(round(cx + half)))
        if x1 > x0:
            mask[y, x0:x1] = True

    if params.branches > 0 and params.branch_len > 0:
        for b in range(params.branches):
            side = -1 if b % 2 == 0 else 1
            by_frac = 0.30 + 0.55 * (b / max(1, params.branches))
            by = int(trunk_top_y + (base_y - trunk_top_y) * (1.0 - by_frac))
            ang = np.deg2rad(params.branch_angle)
            length = params.branch_len * rng.uniform(0.85, 1.15)
            th = max(1, params.branch_thickness)

            t = (by - trunk_top_y) / max(1, params.trunk_h)
            w_at_by = max(1.0, params.trunk_w * (1.0 - params.trunk_taper * (1.0 - t)))
            start_x = cx + side * (w_at_by * 0.5)

            for s in range(int(length)):
                bx = int(round(start_x + side * s * np.sin(ang)))
                by_cur = int(round(by - s * np.cos(ang) * 0.45))
                r = max(1, int(th / 3))
                y0 = max(0, by_cur - r)
                y1 = min(H, by_cur + r + 1)
                x0 = max(0, bx - r)
                x1 = min(W, bx + r + 1)
                if y0 >= y1 or x0 >= x1:
                    continue
                yy = np.arange(y0, y1)[:, None] - by_cur
                xx = np.arange(x0, x1)[None, :] - bx
                mask[y0:y1, x0:x1] |= (yy * yy + xx * xx) <= (r * r)

    return mask


def _colorize_trunk(mask, params, rng):
    H, W = mask.shape
    out = np.zeros((H, W, 3), dtype=np.uint8)
    if not mask.any():
        return out

    base = np.array(params.trunk_color, dtype=np.float32)
    dark = np.clip(base * (1.0 - params.trunk_dark_shift), 0, 255)
    light = np.clip(base + (255 - base) * params.trunk_light_shift, 0, 255)

    noise = rng.random((H, W), dtype=np.float32)
    full = dark[None, None, :] * (1 - noise)[:, :, None] \
        + light[None, None, :] * noise[:, :, None]

    if params.bark_lines:
        for x in range(W):
            if rng.random() < 0.30:
                full[:, x] *= 0.82

    return np.clip(full, 0, 255).astype(np.uint8)


def _crown_shape_probability(kind: str,
                             nx: np.ndarray, ny: np.ndarray) -> np.ndarray:
    """Возвращает «вероятность быть внутри формы» 0..1.

    Для правильных фигур — линейный спад от центра (1) к границе (0),
    чтобы при fill=1.0 форма заполняла весь ограничивающий прямоугольник.
    """
    r = np.sqrt(nx * nx + ny * ny)

    if kind == "round":
        return np.clip(1.0 - r * 0.9, 0.0, 1.0)

    if kind == "cone":
        half_w = np.clip((ny + 1.0) * 0.5, 0.0, 1.0) ** 0.85
        base = np.clip((half_w - np.abs(nx)) * 3.0, 0.0, 1.0)
        layers = 0.5 + 0.5 * np.cos(ny * np.pi * 3.0)
        return np.clip(base * (0.85 + 0.25 * layers ** 2.0), 0.0, 1.0)

    if kind == "narrow":
        d = (nx * nx) / 0.35 + (ny * ny) / 1.05
        return np.clip(1.0 - d, 0.0, 1.0)

    if kind == "column":
        return (np.clip(1.0 - np.abs(nx) * 2.5, 0.0, 1.0) *
                np.clip(1.0 - np.abs(ny) * 0.4, 0.0, 1.0))

    if kind == "palm":
        ang = np.arctan2(ny, nx)
        center = np.clip(1.2 - r * 2.5, 0.0, 1.0)
        petal_signal = 0.5 + 0.5 * np.cos(ang * 7.0)
        petal = (petal_signal ** 2.0) * np.clip(1.0 - r * 1.0, 0.0, 1.0)
        return np.clip(np.maximum(center, petal), 0.0, 1.0)

    if kind == "bush":
        return np.clip(1.0 - r * 1.2, 0.0, 1.0)

    return np.clip(1.0 - r * 0.9, 0.0, 1.0)


def _generate_crown(params: TreeParams, W: int, H: int,
                    cx: float, cy: float, rng: np.random.Generator):
    lp = max(1, int(params.leaf_pixel))
    cells_w = max(3, params.crown_w // lp)
    cells_h = max(3, params.crown_h // lp)

    xs = np.linspace(-1.0, 1.0, cells_w, dtype=np.float32)
    ys = np.linspace(-1.0, 1.0, cells_h, dtype=np.float32)
    NX, NY = np.meshgrid(xs, ys, indexing="ij")

    # 1) Базовая форма: 1 в центре, 0 на краях
    base_prob = _crown_shape_probability(params.crown_type, NX, NY)

    # 2) Рваность краёв: генерация блочного шума
    # Создаем сетку в 6 раз меньше, чтобы "зубы" были крупными
    coarse_w = max(3, cells_w // 6)
    coarse_h = max(3, cells_h // 6)
    coarse = rng.random((coarse_w, coarse_h), dtype=np.float32)
    # Нормализуем от 0 до 1, чтобы шум всегда доходил до крайностей
    coarse = (coarse - coarse.min()) / (coarse.max() - coarse.min() + 1e-6)

    # Растягиваем (upscale) шум до размера кроны через np.repeat
    rep_w = int(np.ceil(cells_w / coarse_w))
    rep_h = int(np.ceil(cells_h / coarse_h))
    edge_noise = np.repeat(np.repeat(coarse, rep_w, axis=0), rep_h, axis=1)
    edge_noise = edge_noise[:cells_w, :cells_h]

    # Добавляем немного мелкого шума (30%), чтобы края не были идеально квадратными
    fine_noise = rng.random((cells_w, cells_h), dtype=np.float32)
    edge_noise = edge_noise * 0.7 + fine_noise * 0.3

    # Масштабируем на base_prob. Коэффициент 2.5 дает сильные "провалы"
    # ВНИМАНИЕ: именно здесь настраивается глубина рваности (2.5)
    signal = base_prob + (edge_noise - 0.5) * params.crown_irregularity * 2.5 * base_prob

    # 3) Порог по заполнению
    fill = max(0.0, min(1.0, params.crown_fill))
    threshold = 0.9 - fill * 0.85
    cells = signal > threshold

    # 4) Дыры внутри (только внутри уже заполненной области)
    if params.crown_holes > 0.01:
        hole_noise = _smooth_grid(
            rng.random((cells_w, cells_h), dtype=np.float32), steps=1)
        cells &= (hole_noise > params.crown_holes)

    # 5) Удаление оторванных кусков
    cells = _keep_largest_component(cells)

    # 6) Оттенки листвы (края темнее)
    thick = _local_thickness(cells)
    noise_lv = rng.random((cells_w, cells_h), dtype=np.float32) * 5.0
    edge_bias = np.clip(2.5 - thick * 0.55, 0.0, 2.5)
    level = noise_lv - edge_bias * 1.2
    leaf = np.clip(np.floor(level).astype(np.int32), 0, 5).astype(np.uint8)

    # 7) Апскейл в размер спрайта
    full_mask = np.zeros((H, W), dtype=bool)
    full_idx = np.zeros((H, W), dtype=np.uint8)

    px = int(round(cx - (cells_w * lp) * 0.5))
    py = int(round(cy - (cells_h * lp) * 0.5))

    for i in range(cells_w):
        for j in range(cells_h):
            if not cells[i, j]:
                continue
            x0 = px + i * lp
            y0 = py + j * lp
            x1 = x0 + lp
            y1 = y0 + lp
            cx0 = max(0, x0); cy0 = max(0, y0)
            cx1 = min(W, x1); cy1 = min(H, y1)
            if cx0 >= cx1 or cy0 >= cy1:
                continue
            full_mask[cy0:cy1, cx0:cx1] = True
            full_idx[cy0:cy1, cx0:cx1] = leaf[i, j]

    return full_mask, full_idx

def _smooth_grid(grid: np.ndarray, steps: int) -> np.ndarray:
    out = grid.copy()
    for _ in range(steps):
        out = (out + np.roll(out, 1, 0) + np.roll(out, -1, 0) +
               np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 5.0
    return out


def _keep_largest_component(cells: np.ndarray) -> np.ndarray:
    cw, ch = cells.shape
    visited = np.zeros_like(cells, dtype=bool)
    best_component = []

    for i in range(cw):
        for j in range(ch):
            if cells[i, j] and not visited[i, j]:
                q = [(i, j)]
                visited[i, j] = True
                comp = []
                while q:
                    cx, cy = q.pop(0)
                    comp.append((cx, cy))
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nx, ny = cx + dx, cy + dy
                        if (0 <= nx < cw and 0 <= ny < ch
                                and cells[nx, ny] and not visited[nx, ny]):
                            visited[nx, ny] = True
                            q.append((nx, ny))
                if len(comp) > len(best_component):
                    best_component = comp

    result = np.zeros_like(cells)
    for (x, y) in best_component:
        result[x, y] = True
    return result


def _local_thickness(cells: np.ndarray) -> np.ndarray:
    cw, ch = cells.shape
    out = np.zeros((cw, ch), dtype=np.float32)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            out += np.roll(np.roll(cells, di, 0), dj, 1).astype(np.float32)
    return out


def _leaf_palette(params: TreeParams) -> np.ndarray:
    base1 = np.array(params.leaf_color, dtype=np.float32)
    base2 = np.array(params.leaf_color2, dtype=np.float32)
    palette = []
    for i in range(6):
        t = i / 5.0
        c = base1 * (1.0 - t) + base2 * t
        if i < 3:
            k = 1.0 - params.leaf_dark_shift * ((3 - i) / 3.0) * 0.7
            c = c * k
        else:
            k = params.leaf_light_shift * ((i - 2) / 3.0) * 0.6
            c = c + (255.0 - c) * k
        palette.append(np.clip(c, 0, 255))
    return np.array(palette, dtype=np.uint8)
