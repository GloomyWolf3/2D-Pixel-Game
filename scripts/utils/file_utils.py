# scripts/utils/file_utils.py
import json
import os
import shutil
from datetime import datetime

from scripts.config import settings


def ensure_dirs() -> None:
    os.makedirs(settings.SAVES_DIR, exist_ok=True)
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    os.makedirs(settings.TEXTURES_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.TEXTURES_DIR, "generated"), exist_ok=True)


def _meta_path(folder: str) -> str:
    return os.path.join(settings.SAVES_DIR, folder, "meta.json")


def list_saves() -> list[dict]:
    """Возвращает список метаданных всех сохранений."""
    saves: list[dict] = []
    if not os.path.isdir(settings.SAVES_DIR):
        return saves

    for name in os.listdir(settings.SAVES_DIR):
        path = os.path.join(settings.SAVES_DIR, name)
        meta_path = _meta_path(name)
        if not os.path.isdir(path) or not os.path.isfile(meta_path):
            continue
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["folder"] = name
            saves.append(meta)
        except (OSError, json.JSONDecodeError):
            continue

    saves.sort(key=lambda m: m.get("last_played", ""), reverse=True)
    return saves


def _sanitize_folder(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in " _-").strip()
    return safe or "world"


def create_save(name: str, seed: int, size: str,
                noise_kind: str = "value") -> tuple[str, dict]:
    """Создаёт папку нового сохранения и возвращает (folder, meta)."""
    base = _sanitize_folder(name)
    folder = base
    i = 1
    while os.path.exists(os.path.join(settings.SAVES_DIR, folder)):
        folder = f"{base}_{i}"
        i += 1

    path = os.path.join(settings.SAVES_DIR, folder)
    os.makedirs(path, exist_ok=True)

    now = datetime.now().isoformat(timespec="seconds")
    meta = {
        "name": name,
        "seed": seed,
        "size": size,
        "noise_kind": noise_kind,
        "created": now,
        "last_played": now,
        "version": 1,
    }
    with open(_meta_path(folder), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return folder, meta


def load_meta(folder: str) -> dict | None:
    path = _meta_path(folder)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["folder"] = folder
        return meta
    except (OSError, json.JSONDecodeError):
        return None


def update_last_played(folder: str) -> None:
    meta = load_meta(folder)
    if not meta:
        return
    meta["last_played"] = datetime.now().isoformat(timespec="seconds")
    meta.pop("folder", None)
    with open(_meta_path(folder), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def delete_save(folder: str) -> None:
    path = os.path.join(settings.SAVES_DIR, folder)
    if os.path.isdir(path):
        shutil.rmtree(path)
        
        
        