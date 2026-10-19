# scripts/texture_gen/tree_library.py
"""Сохранение/загрузка наборов деревьев."""
from __future__ import annotations

import json
import os
import shutil
import random
from datetime import datetime

import pygame

from scripts.config import settings
from scripts.texture_gen.tree_generator import generate_tree_surface
from scripts.texture_gen.tree_params import TreeParams


def trees_dir() -> str:
    return os.path.join(settings.TEXTURES_DIR, "trees")

def ensure_dirs() -> None:
    os.makedirs(trees_dir(), exist_ok=True)

def _active_file() -> str:
    return os.path.join(trees_dir(), "active.txt")

def list_tree_sets() -> list[str]:
    d = trees_dir()
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d)
                  if os.path.isdir(os.path.join(d, n)))

def save_tree_set(name: str, tree_params: dict[str, TreeParams], force_folder: str | None = None) -> str:
    ensure_dirs()
    
    if force_folder:
        folder = force_folder
    else:
        safe = "".join(c for c in name if c.isalnum() or c in " _-").strip() or "trees"
        folder = safe
        i = 1
        while os.path.exists(os.path.join(trees_dir(), folder)):
            folder = f"{safe}_{i}"
            i += 1
            
    path = os.path.join(trees_dir(), folder)
    if os.path.exists(path):
        shutil.rmtree(path)  # Удаляем старую версию перед перезаписью
    os.makedirs(path, exist_ok=True)

    meta = {
        "name": folder,
        "created": datetime.now().isoformat(timespec="seconds"),
        "version": 2,
        "trees": {},
    }
    for kind, params in tree_params.items():
        files = []
        # Генерируем пачку вариаций
        for v_idx in range(params.variants_count):
            p = params.copy()
            p.seed = random.randint(0, 2**31 - 1)
            
            # Рандомизируем параметры в заданных диапазонах
            p.trunk_h = int(random.uniform(*params.var_trunk_h))
            p.crown_w = int(random.uniform(*params.var_crown_w))
            p.crown_h = int(random.uniform(*params.var_crown_h))
            p.crown_irregularity = random.uniform(*params.var_crown_irregularity)
            p.crown_holes = random.uniform(*params.var_crown_holes)
            
            surf = generate_tree_surface(p)
            fname = f"{kind}_{v_idx}.png"
            pygame.image.save(surf, os.path.join(path, fname))
            files.append(fname)
            
        meta["trees"][kind] = {
            "files": files,
            "params": params.to_dict(),
        }

    with open(os.path.join(path, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return folder

def load_tree_params(folder: str) -> dict[str, TreeParams]:
    path = os.path.join(trees_dir(), folder, "meta.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    out: dict[str, TreeParams] = {}
    for kind, entry in meta.get("trees", {}).items():
        out[kind] = TreeParams.from_dict(entry["params"])
    return out

def load_tree_surfaces(folder: str) -> dict[str, list[pygame.Surface]]:
    path = os.path.join(trees_dir(), folder)
    out: dict[str, list[pygame.Surface]] = {}
    if not os.path.isdir(path):
        return out
    for fname in os.listdir(path):
        if fname.endswith(".png") and "_" in fname:
            stem = fname[:-4]
            kind, idx_str = stem.rsplit("_", 1)
            if idx_str.isdigit():
                try:
                    surf = pygame.image.load(os.path.join(path, fname)).convert_alpha()
                    out.setdefault(kind, []).append(surf)
                except pygame.error:
                    pass
    return out

def delete_tree_set(folder: str) -> None:
    path = os.path.join(trees_dir(), folder)
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

