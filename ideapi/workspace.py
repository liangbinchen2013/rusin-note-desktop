"""文件工作区：把笔记以 .md 文件落到用户可选目录，像网盘一样本地缓存。

两类目录：
- 本地笔记目录：本地笔记的 md 镜像（默认 data/local_notes，可在设置里改）
- 云端缓存目录：云端笔记的本地副本（默认系统临时目录，可在设置里改）

每个笔记对应一个 .md 文件（纯正文），元数据保存在目录内的 _index.json。
文件名用「安全标题__笔记ID.md」保证唯一，标题变化也不会覆盖其它笔记。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from cloudsync import settings as settings_store

INDEX_NAME = "_index.json"
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _data_dir() -> Path:
    path = Path(os.environ.get("RUSIN_DATA_DIR", "data"))
    return path if path.is_absolute() else Path.cwd() / path


def local_root() -> Path:
    configured = str(settings_store.load_settings().get("local_notes_dir") or "").strip()
    path = Path(configured).expanduser() if configured else _data_dir() / "local_notes"
    return path


def cloud_root() -> Path:
    configured = str(settings_store.load_settings().get("cloud_cache_dir") or "").strip()
    if configured:
        path = Path(configured).expanduser()
    else:
        path = Path(tempfile.gettempdir()) / "rusin-note-cloud"
    return path


def safe_name(title: str, note_id: str) -> str:
    base = _BAD_CHARS.sub("_", str(title or "").strip())[:60].strip(" .")
    base = base or "note"
    return f"{base}__{note_id}.md"


def ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_index(root: Path) -> dict:
    try:
        raw = json.loads((root / INDEX_NAME).read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def save_index(root: Path, index: dict) -> None:
    ensure(root)
    target = root / INDEX_NAME
    tmp = root / (INDEX_NAME + ".tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, target)


def file_path(root: Path, meta: dict) -> Path:
    return root / str(meta.get("file") or safe_name(meta.get("title", ""), meta.get("id", "")))


def list_files(root: Path) -> list[dict]:
    ensure(root)
    index = load_index(root)
    result = []
    for note_id, meta in index.items():
        if not isinstance(meta, dict):
            continue
        path = file_path(root, meta)
        if not path.is_file():
            continue
        result.append({
            "id": note_id,
            "title": meta.get("title") or note_id,
            "folder": meta.get("folder") or "",
            "tags": meta.get("tags") or [],
            "file": path.name,
            "size": path.stat().st_size,
            "mtime": meta.get("mtime") or path.stat().st_mtime,
        })
    result.sort(key=lambda item: (item.get("folder") or "", item.get("title") or ""))
    return result


def read_file(root: Path, note_id: str) -> dict | None:
    meta = load_index(root).get(note_id)
    if not isinstance(meta, dict):
        return None
    path = file_path(root, meta)
    if not path.is_file():
        return None
    return {
        "id": note_id,
        "title": meta.get("title") or note_id,
        "folder": meta.get("folder") or "",
        "tags": meta.get("tags") or [],
        "content": path.read_text(encoding="utf-8"),
        "file": path.name,
    }


def write_file(root: Path, note_id: str, content: str, title: str = "", folder: str = "", tags=None) -> dict:
    ensure(root)
    index = load_index(root)
    meta = index.get(note_id) if isinstance(index.get(note_id), dict) else {}
    old_file = meta.get("file")
    new_file = safe_name(title or meta.get("title") or note_id, note_id)
    (root / new_file).write_text(content or "\n", encoding="utf-8")
    if old_file and old_file != new_file:
        try:
            (root / old_file).unlink()
        except OSError:
            pass
    import time
    meta.update({
        "id": note_id,
        "title": title or meta.get("title") or note_id,
        "folder": folder or "",
        "tags": tags or meta.get("tags") or [],
        "file": new_file,
        "mtime": time.time(),
    })
    index[note_id] = meta
    save_index(root, index)
    return meta


def remove_file(root: Path, note_id: str) -> None:
    index = load_index(root)
    meta = index.get(note_id)
    if isinstance(meta, dict) and meta.get("file"):
        try:
            (root / meta["file"]).unlink()
        except OSError:
            pass
    index.pop(note_id, None)
    save_index(root, index)
