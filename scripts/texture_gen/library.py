# scripts/texture_gen/library.py
"""Сохранение/загрузка наборов текстур блоков."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime

import pygame

from scripts.config import settings
from scripts.game_logic import tiles as T
from scripts.texture_gen.generator import generate_surface
from scripts.texture_gen.params import TextureParams


# ---------------------------------------------------------------------------
# Пресеты по умолчанию (стартовая точка для редактора)
# ---------------------------------------------------------------------------
PRESETS: dict[int, TextureParams] = {
    T.DIRT: TextureParams(
        base_color=(110, 70, 40), noise_scale=4, noise_intensity=0.45,
        veins=True, vein_scale=3, vein_intensity=0.18, vein_color=(70, 45, 25),
        speckles=True, speckle_scale=2, speckle_intensity=0.10,
        speckle_color=(80, 50, 30),
    ),
    T.GRASS: TextureParams(
        base_color=(70, 140, 60), noise_scale=3, noise_intensity=0.35,
        speckles=True, speckle_scale=2, speckle_intensity=0.18,
        speckle_color=(120, 190, 80),
    ),
    T.STONE: TextureParams(
        base_color=(100, 100, 110), noise_scale=4, noise_octaves=3,
        noise_intensity=0.40,
        cracks=True, crack_scale=3, crack_intensity=0.10,
        crack_color=(50, 50, 60),
    ),
    T.SAND: TextureParams(
        base_color=(222, 202, 132), noise_scale=5, noise_intensity=0.22,
        speckles=True, speckle_scale=2, speckle_intensity=0.12,
        speckle_color=(190, 170, 100),
    ),
    T.WATER: TextureParams(
        base_color=(58, 108, 198), noise_scale=6, noise_intensity=0.28,
        dark_shift=0.15, light_shift=0.25,
    ),
    T.SANDSTONE: TextureParams(
        base_color=(198, 158, 88), noise_scale=4, noise_intensity=0.28,
        speckles=True, speckle_scale=3, speckle_intensity=0.10,
        speckle_color=(160, 120, 60),
    ),
    T.SNOW: TextureParams(
        base_color=(232, 236, 246), noise_scale=5, noise_intensity=0.15,
        speckles=True, speckle_scale=2, speckle_intensity=0.08,
        speckle_color=(200, 210, 230),
    ),
    T.ICE: TextureParams(
        base_color=(150, 200, 230), noise_scale=4, noise_intensity=0.28,
        cracks=True, crack_scale=3, crack_intensity=0.08,
        crack_color=(90, 140, 180),
    ),
    T.BEDROCK: TextureParams(
        base_color=(28, 28, 34), noise_scale=3, noise_intensity=0.55,
        dark_shift=0.20, light_shift=0.50,
        cracks=True, crack_scale=2, crack_intensity=0.15,
        crack_color=(60, 55, 60),
    ),
}

TILE_LABELS = {
    T.DIRT: "Земля",
    T.GRASS: "Трава",
    T.STONE: "Камень",
    T.SAND: "Песок",
    T.WATER: "Вода",
    T.SANDSTONE: "Песчаник",
    T.SNOW: "Снег",
    T.ICE: "Лёд",
    T.BEDROCK: "Бедрок",
}


# ---------------------------------------------------------------------------
# Пути
# ---------------------------------------------------------------------------
def sets_dir() -> str:
    return os.path.join(settings.TEXTURES_DIR, "generated")


def ensure_dirs() -> None:
    os.makedirs(sets_dir(), exist_ok=True)


def _active_file() -> str:
    return os.path.join(sets_dir(), "active.txt")


# ---------------------------------------------------------------------------
# Список наборов
# ---------------------------------------------------------------------------
def list_sets() -> list[str]:
    d = sets_dir()
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d)
                  if os.path.isdir(os.path.join(d, n)))


# ---------------------------------------------------------------------------
# Сохранение набора: 9 вариаций на каждый тайл
# ---------------------------------------------------------------------------
def save_set(name: str, tile_params: dict[int, TextureParams]) -> str:
    ensure_dirs()
    safe = "".join(c for c in name if c.isalnum() or c in " _-").strip() or "set"
    folder = safe
    i = 1
    while os.path.exists(os.path.join(sets_dir(), folder)):
        folder = f"{safe}_{i}"
        i += 1

    path = os.path.join(sets_dir(), folder)
    os.makedirs(path, exist_ok=True)

    meta = {
        "name": name,
        "created": datetime.now().isoformat(timespec="seconds"),
        "version": 2,
        "variants": 9,
        "tiles": {},
    }

    for tid, params in tile_params.items():
        files: list[str] = []
        for idx in range(9):
            p = params.copy()
            p.seed = params.seed + idx
            surf = generate_surface(p)
            fname = f"tile_{tid}_{idx}.png"
            pygame.image.save(surf, os.path.join(path, fname))
            files.append(fname)
        meta["tiles"][str(tid)] = {
            "files": files,
            "params": params.to_dict(),
        }

    with open(os.path.join(path, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return folder


# ---------------------------------------------------------------------------
# Загрузка параметров (для редактора)
# ---------------------------------------------------------------------------
def load_params(folder: str) -> dict[int, TextureParams]:
    path = os.path.join(sets_dir(), folder, "meta.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    result: dict[int, TextureParams] = {}
    for tid_str, entry in meta.get("tiles", {}).items():
        try:
            tid = int(tid_str)
        except ValueError:
            continue
        result[tid] = TextureParams.from_dict(entry["params"])
    return result


# ---------------------------------------------------------------------------
# Загрузка поверхностей — списком вариаций
# ---------------------------------------------------------------------------
def load_surfaces(folder: str, size: int) -> dict[int, list[pygame.Surface]]:
    """{tile_id: [Surface, ...]}.

    Совместимо со старым форматом (один файл → список из 1 элемента).
    """
    path = os.path.join(sets_dir(), folder)
    result: dict[int, list[pygame.Surface]] = {}
    if not os.path.isdir(path):
        return result

    meta_path = os.path.join(path, "meta.json")
    files_by_tid: dict[int, list[str]] = {}

    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        for tid_str, entry in meta.get("tiles", {}).items():
            try:
                tid = int(tid_str)
            except ValueError:
                continue
            if "files" in entry and isinstance(entry["files"], list):
                files_by_tid[tid] = list(entry["files"])
            elif "file" in entry:
                files_by_tid[tid] = [entry["file"]]

    # Резервный путь — просто сканируем папку
    if not files_by_tid:
        for fname in os.listdir(path):
            if not fname.startswith("tile_") or not fname.endswith(".png"):
                continue
            stem = fname[5:-4]
            parts = stem.split("_")
            try:
                tid = int(parts[0])
            except ValueError:
                continue
            files_by_tid.setdefault(tid, []).append(fname)

    for tid, fnames in files_by_tid.items():
        surfs: list[pygame.Surface] = []
        for fname in fnames:
            fp = os.path.join(path, fname)
            if not os.path.isfile(fp):
                continue
            try:
                surf = pygame.image.load(fp).convert()
            except pygame.error:
                continue
            if surf.get_width() != size:
                surf = pygame.transform.scale(surf, (size, size))
            surfs.append(surf)
        if surfs:
            result[tid] = surfs
    return result


# ---------------------------------------------------------------------------
# Удаление / активный набор
# ---------------------------------------------------------------------------
def delete_set(folder: str) -> None:
    path = os.path.join(sets_dir(), folder)
    if os.path.isdir(path):
        shutil.rmtree(path)
    if get_active() == folder:
        set_active(None)


def set_active(folder: str | None) -> None:
    path = _active_file()
    if folder:
        ensure_dirs()
        with open(path, "w", encoding="utf-8") as f:
            f.write(folder)
    elif os.path.isfile(path):
        os.remove(path)


def get_active() -> str | None:
    path = _active_file()
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    return None


# ---------------------------------------------------------------------------
# Заготовки для предметов (пока не используются в игре)
# ---------------------------------------------------------------------------
def item_sets_dir() -> str:
    return os.path.join(settings.TEXTURES_DIR, "items")


def ensure_item_dirs() -> None:
    os.makedirs(item_sets_dir(), exist_ok=True)


def _item_active_file() -> str:
    return os.path.join(item_sets_dir(), "active.txt")


def list_item_sets() -> list[str]:
    d = item_sets_dir()
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d)
                  if os.path.isdir(os.path.join(d, n)))


def set_active_items(folder: str | None) -> None:
    path = _item_active_file()
    if folder:
        ensure_item_dirs()
        with open(path, "w", encoding="utf-8") as f:
            f.write(folder)
    elif os.path.isfile(path):
        os.remove(path)


def get_active_items() -> str | None:
    path = _item_active_file()
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    return None


def delete_item_set(folder: str) -> None:
    path = os.path.join(item_sets_dir(), folder)
    if os.path.isdir(path):
        shutil.rmtree(path)
    if get_active_items() == folder:
        set_active_items(None)
        
        