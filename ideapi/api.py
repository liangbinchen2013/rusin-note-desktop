"""本地 IDE API：只监听 127.0.0.1，免登录，直接读写本地用户数据。"""

from __future__ import annotations

import time

from flask import Blueprint, jsonify, request

from app.core import auth, config, folders, notes, store, tags
from app.core.extensions import csrf

bp = Blueprint("ide_api", __name__, url_prefix="/api/ide")
csrf.exempt(bp)  # 本机回环地址使用，且没有跨站 Cookie 认证


def _local_user() -> str:
    """决定 IDE 使用的本地用户：优先同步设置，其次 local/管理员/唯一用户。"""
    from cloudsync import settings as sync_settings

    configured = (sync_settings.load_settings().get("local_user") or "").strip()
    users = sorted(store.users.keys())
    if configured and configured in users:
        return configured
    if "local" in users:
        return "local"
    for candidate in config.config.get("admin_users", []) or []:
        if candidate in users:
            return candidate
    if users:
        return users[0]

    # 首次启动：自动创建本地账号，不需要登录页
    salt = auth.generate_salt()
    password = auth.generate_session_token()
    store.register_user("local", {
        "salt": salt,
        "hash": auth.hash_password(password, salt),
        "created_by": "ide",
    })
    return "local"


def _note_rows(user: str) -> list[dict]:
    rows = notes.list_user_notes_detailed(user)
    folder_map = folders.get_user_note_folders(user)
    tag_map = tags.get_user_note_tags(user)
    result = []
    for row in rows:
        note_id = row["id"]
        title = (row.get("title") or "").strip() or note_id
        result.append({
            "id": note_id,
            "title": title,
            "folder": folder_map.get(note_id, "") or "",
            "tags": tag_map.get(note_id, []) or [],
            "mtime": row.get("mtime") or 0,
            "size": row.get("size") or 0,
        })
    return result


@bp.get("/bootstrap")
def bootstrap():
    user = _local_user()
    rows = _note_rows(user)
    from cloudsync import settings as sync_settings
    settings = sync_settings.load_settings()
    return jsonify({
        "user": user,
        "siteName": config.SITE_NAME or "如形本地笔记",
        "notes": rows,
        "stats": {
            "count": len(rows),
            "size": sum(row["size"] for row in rows),
        },
        "syncConfigured": bool(settings.get("remote_url") and settings.get("session_cookie")),
    })


@bp.get("/notes/<note_id>")
def get_note(note_id: str):
    user = _local_user()
    content = notes.read_note(user, note_id)
    if not notes.note_exists(user, note_id):
        return jsonify({"error": "笔记不存在"}), 404
    return jsonify({
        "id": note_id,
        "content": content,
        "tags": tags.get_note_tags(user, note_id),
        "folder": folders.get_note_folder(user, note_id),
        "mtime": notes.get_note_mtime(user, note_id) or 0,
    })


@bp.post("/notes")
def create_note():
    user = _local_user()
    folder = str((request.get_json(silent=True) or {}).get("folder") or "")
    for _ in range(20):
        note_id = notes.generate_random_id()
        if not notes.note_exists(user, note_id):
            break
    else:
        return jsonify({"error": "无法生成唯一笔记 ID"}), 500
    # 空内容会被后端视为删除，写入一个换行保持笔记存在
    if not notes.write_note(user, note_id, "\n"):
        return jsonify({"error": "创建失败"}), 500
    if folder:
        folders.set_note_folder(user, note_id, folder)
    return jsonify({"id": note_id}), 201


@bp.put("/notes/<note_id>")
def save_note(note_id: str):
    user = _local_user()
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    if not isinstance(content, str):
        return jsonify({"error": "content 必须是字符串"}), 400
    note_tags = payload.get("tags", [])
    if isinstance(note_tags, str):
        note_tags = [t.strip() for t in note_tags.split(",") if t.strip()]
    if not isinstance(note_tags, list):
        note_tags = []
    folder = str(payload.get("folder") or "")

    if not notes.note_exists(user, note_id) and not content.strip():
        return jsonify({"error": "新笔记不能为空"}), 400
    if not notes.write_note(user, note_id, content):
        return jsonify({"error": "保存失败"}), 500
    tags.set_note_tags(user, note_id, note_tags)
    folders.set_note_folder(user, note_id, folder)
    return jsonify({"ok": True, "mtime": notes.get_note_mtime(user, note_id) or 0})


@bp.delete("/notes/<note_id>")
def delete_note(note_id: str):
    user = _local_user()
    notes.write_note(user, note_id, "")  # 后端会级联清理标签/文件夹/置顶
    return jsonify({"ok": True})


@bp.get("/search")
def search():
    user = _local_user()
    query = (request.args.get("q") or "").strip().lower()
    results = []
    for row in _note_rows(user):
        content = notes.read_note(user, row["id"])
        haystack = f"{row['title']} {row['id']} {' '.join(row['tags'])} {content}".lower()
        if not query or query in haystack:
            position = content.lower().find(query) if query else 0
            snippet = content[max(0, position - 40):position + 120].replace("\n", " ") if query else content[:120]
            results.append({**row, "snippet": snippet})
        if len(results) >= 50:
            break
    return jsonify({"items": results})


@bp.get("/sync/status")
def sync_status():
    from cloudsync import service as sync_service
    from cloudsync import settings as sync_settings

    settings = sync_settings.load_settings()
    state = sync_settings.load_state()
    connection = {"ok": False, "message": "尚未配置云端地址与登录态"}
    if request.args.get("check") == "1" and settings.get("remote_url") and settings.get("session_cookie"):
        try:
            ok, message = sync_service.make_client(settings).check_connection()
            connection = {"ok": ok, "message": message}
        except Exception as exc:
            connection = {"message": str(exc)}
    return jsonify({
        "settings": {
            "remote_url": settings.get("remote_url", ""),
            "remote_user": settings.get("remote_user", ""),
            "local_user": settings.get("local_user", ""),
            "cookie_configured": bool(settings.get("session_cookie")),
            "overwrite_remote": bool(settings.get("overwrite_remote")),
            "overwrite_local": bool(settings.get("overwrite_local")),
            "pull_pages": settings.get("pull_pages", 1),
            "request_delay": settings.get("request_delay", 0.3),
        },
        "connection": connection,
        "stats": {
            "pushed_notes": len(state["notes"]),
            "pulled_notes": len(state["remote_notes"]),
            "benben_seen": len(state["benben_seen"]),
        },
        "runs": state["runs"][:20],
    })


@bp.put("/sync/settings")
def save_sync_settings():
    from cloudsync import settings as sync_settings

    payload = request.get_json(silent=True) or {}
    current = sync_settings.load_settings()
    merged = dict(current)
    for key in (
        "remote_url", "remote_user", "local_user", "overwrite_remote",
        "overwrite_local", "pull_pages", "request_delay",
    ):
        if key in payload:
            merged[key] = payload[key]
    cookie = payload.get("session_cookie")
    if cookie:  # 留空表示沿用已保存的 Cookie
        merged["session_cookie"] = str(cookie).strip()
    url = str(merged.get("remote_url") or "").strip().rstrip("/")
    if url and "://" not in url:
        url = ("http://" if url.startswith(("localhost", "127.0.0.1")) else "https://") + url
    merged["remote_url"] = url
    try:
        sync_settings.save_settings(merged)
    except OSError as exc:
        return jsonify({"error": f"保存失败：{exc}"}), 500
    return jsonify({"ok": True})


@bp.post("/sync/<action>")
def run_sync(action: str):
    from cloudsync import service as sync_service
    from cloudsync import settings as sync_settings

    handlers = {
        "test": sync_service.test_connection,
        "pull_benben": sync_service.pull_benben,
        "pull_notes": sync_service.pull_notes,
        "push_notes": sync_service.push_notes,
        "push_benben": sync_service.push_benben,
        "sync_all": sync_service.sync_all,
    }
    handler = handlers.get(action)
    if handler is None:
        return jsonify({"error": "未知操作"}), 404
    settings = sync_settings.load_settings()
    try:
        report = handler(settings)
    except Exception as exc:
        report = {"ok": 0, "skipped": 0, "failed": 1, "details": [f"未预期错误：{exc}"]}
    sync_settings.record_run(action, report)
    return jsonify(report)
