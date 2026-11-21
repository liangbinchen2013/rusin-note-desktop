"""同步配置与状态：保存在本地 data/ 目录，登录 Cookie 加密落盘。"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import tempfile
import time
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

DEFAULT_SETTINGS = {
    "remote_url": "",
    "remote_user": "",
    "session_cookie": "",
    "local_user": "",
    "overwrite_remote": False,
    "overwrite_local": True,
    "pull_pages": 1,
    "request_delay": 0.3,
    # 工作区目录：留空表示使用默认位置（本地=data/local_notes，云端=系统临时目录）
    "local_notes_dir": "",
    "cloud_cache_dir": "",
}

DEFAULT_STATE = {
    "notes": {},          # 本地笔记 id -> {hash, pushed_at, remote_url}
    "remote_notes": {},   # 云端笔记 id -> {hash, pulled_at}
    "benben_seen": [],    # 已拉取的犇犇签名
    "pushed_benben": [],  # 已推送的本地犇犇签名
    "runs": [],           # 最近运行记录
}


def data_dir() -> Path:
    path = Path(os.environ.get("RUSIN_DATA_DIR", "data"))
    return path if path.is_absolute() else Path.cwd() / path


def _settings_path() -> Path:
    return data_dir() / "sync_settings.json"


def _state_path() -> Path:
    return data_dir() / "sync_state.json"


def _key_path() -> Path:
    return data_dir() / "sync.key"


def _fernet() -> Fernet:
    path = _key_path()
    try:
        key_text = path.read_text(encoding="utf-8").strip()
    except OSError:
        key_text = ""
    if not key_text:
        key_text = secrets.token_hex(32)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key_text, encoding="utf-8")
    digest = hashlib.sha256(key_text.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def load_settings() -> dict:
    result = dict(DEFAULT_SETTINGS)
    try:
        raw = json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return result
    if not isinstance(raw, dict):
        return result
    for key in result:
        if key in raw:
            result[key] = raw[key]
    encrypted = raw.get("session_cookie_enc")
    if encrypted:
        try:
            result["session_cookie"] = _fernet().decrypt(encrypted.encode()).decode()
        except (InvalidToken, ValueError, UnicodeDecodeError):
            result["session_cookie"] = ""
    return result


def save_settings(settings: dict) -> None:
    payload = dict(DEFAULT_SETTINGS)
    payload.update({k: v for k, v in settings.items() if k in DEFAULT_SETTINGS})
    cookie = str(payload.get("session_cookie") or "").strip()
    payload.pop("session_cookie", None)
    payload["session_cookie_enc"] = (
        _fernet().encrypt(cookie.encode()).decode() if cookie else ""
    )
    _atomic_write(_settings_path(), payload)


def load_state() -> dict:
    try:
        raw = json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    state = dict(DEFAULT_STATE)
    if isinstance(raw, dict):
        state.update({k: raw[k] for k in state if k in raw})
    for key in ("notes", "remote_notes"):
        if not isinstance(state[key], dict):
            state[key] = {}
    for key in ("benben_seen", "pushed_benben", "runs"):
        if not isinstance(state[key], list):
            state[key] = []
    return state


def save_state(state: dict) -> None:
    _atomic_write(_state_path(), state)


def record_run(action: str, report: dict) -> None:
    state = load_state()
    state["runs"].insert(0, {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "report": report,
    })
    state["runs"] = state["runs"][:20]
    save_state(state)
