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
    from app.core import note_titles

    rows = notes.list_user_notes_detailed(user)
    folder_map = folders.get_user_note_folders(user)
    tag_map = tags.get_user_note_tags(user)
    title_map = note_titles.get_user_note_titles(user)
    result = []
    for row in rows:
        note_id = row["id"]
        title = (
            title_map.get(note_id, "").strip()
            or (row.get("title") or "").strip()
            or note_id
        )
        result.append({
            "id": note_id,
            "title": title,
            "folder": folder_map.get(note_id, "") or "",
            "tags": tag_map.get(note_id, []) or [],
            "mtime": row.get("mtime") or 0,
            "size": row.get("size") or 0,
        })
    return result


def _mirror_local_note(user: str, note_id: str, content: str, title: str, folder: str, tags_list: list) -> None:
    """把本地笔记同步一份 md 到工作区目录（失败不影响主流程）。"""
    try:
        from . import workspace

        workspace.write_file(workspace.local_root(), note_id, content, title, folder, tags_list)
    except Exception:
        pass


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
    from app.core import note_titles

    user = _local_user()
    content = notes.read_note(user, note_id)
    if not notes.note_exists(user, note_id):
        return jsonify({"error": "笔记不存在"}), 404
    return jsonify({
        "id": note_id,
        "content": content,
        "title": note_titles.get_note_title(user, note_id)
        or notes.note_title(user, note_id) or note_id,
        "tags": tags.get_note_tags(user, note_id),
        "folder": folders.get_note_folder(user, note_id),
        "mtime": notes.get_note_mtime(user, note_id) or 0,
    })


@bp.post("/notes")
def create_note():
    user = _local_user()
    from app.core import note_titles

    payload = request.get_json(silent=True) or {}
    folder = str(payload.get("folder") or "")
    title = note_titles.clean_title(payload.get("title") or "")
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
    if title:
        note_titles.set_note_title(user, note_id, title)
    _mirror_local_note(user, note_id, "\n", title or note_id, folder, [])
    return jsonify({"id": note_id}), 201


@bp.put("/notes/<note_id>")
def save_note(note_id: str):
    from app.core import note_titles

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
    title = note_titles.clean_title(payload.get("title") or "")

    if not notes.note_exists(user, note_id) and not content.strip():
        return jsonify({"error": "新笔记不能为空"}), 400
    if not notes.write_note(user, note_id, content):
        return jsonify({"error": "保存失败"}), 500
    tags.set_note_tags(user, note_id, note_tags)
    folders.set_note_folder(user, note_id, folder)
    if title:
        note_titles.set_note_title(user, note_id, title)
    _mirror_local_note(user, note_id, content, title or note_id, folder, note_tags)
    return jsonify({"ok": True, "mtime": notes.get_note_mtime(user, note_id) or 0})


@bp.delete("/notes/<note_id>")
def delete_note(note_id: str):
    from app.core import note_titles
    from . import workspace

    user = _local_user()
    notes.write_note(user, note_id, "")  # 后端会级联清理标签/文件夹/置顶
    note_titles.delete_note_title(user, note_id)
    try:
        workspace.remove_file(workspace.local_root(), note_id)
    except Exception:
        pass
    return jsonify({"ok": True})


@bp.post("/notes/save-as")
def save_as_note():
    """按用户指定名称另存为新笔记，返回新 ID。"""
    from app.core import note_titles

    user = _local_user()
    payload = request.get_json(silent=True) or {}
    title = note_titles.clean_title(payload.get("title") or "")
    if not title:
        return jsonify({"error": "请填写名称"}), 400
    content = payload.get("content")
    if not isinstance(content, str):
        content = "\n"
    note_tags = payload.get("tags", [])
    if isinstance(note_tags, str):
        note_tags = [t.strip() for t in note_tags.split(",") if t.strip()]
    if not isinstance(note_tags, list):
        note_tags = []
    folder = str(payload.get("folder") or "")
    for _ in range(20):
        note_id = notes.generate_random_id()
        if not notes.note_exists(user, note_id):
            break
    else:
        return jsonify({"error": "无法生成唯一笔记 ID"}), 500
    if not notes.write_note(user, note_id, content or "\n"):
        return jsonify({"error": "另存为失败"}), 500
    note_titles.set_note_title(user, note_id, title)
    if note_tags:
        tags.set_note_tags(user, note_id, note_tags)
    if folder:
        folders.set_note_folder(user, note_id, folder)
    _mirror_local_note(user, note_id, content, title, folder, note_tags)
    return jsonify({"id": note_id}), 201


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


def _remote_settings():
    from cloudsync import settings as sync_settings

    settings = sync_settings.load_settings()
    if not settings.get("remote_url") or not settings.get("session_cookie"):
        return None
    return settings


@bp.get("/remote/status")
def remote_status():
    from cloudsync import settings as sync_settings

    settings = sync_settings.load_settings()
    configured = bool(settings.get("remote_url") and settings.get("session_cookie"))
    return jsonify({
        "configured": configured,
        "user": settings.get("remote_user", "") if configured else "",
        "url": settings.get("remote_url", "") if configured else "",
    })


@bp.get("/remote/notes")
def remote_notes():
    from cloudsync import service as sync_service

    settings = _remote_settings()
    if not settings:
        return jsonify({"error": "尚未配置云端站点与登录态"}), 400
    try:
        return jsonify({"notes": sync_service.remote_note_rows(settings)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@bp.get("/remote/notes/<note_id>")
def get_remote_note(note_id: str):
    from cloudsync import service as sync_service

    settings = _remote_settings()
    if not settings:
        return jsonify({"error": "尚未配置云端站点与登录态"}), 400
    try:
        note = sync_service.make_client(settings).read_note(note_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(note)


@bp.post("/remote/notes")
def create_remote_note():
    from cloudsync import service as sync_service

    settings = _remote_settings()
    if not settings:
        return jsonify({"error": "尚未配置云端站点与登录态"}), 400
    folder = str((request.get_json(silent=True) or {}).get("folder") or "")
    try:
        note_id = sync_service.make_client(settings).create_note(folder)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"id": note_id}), 201


@bp.put("/remote/notes/<note_id>")
def save_remote_note(note_id: str):
    from cloudsync import service as sync_service

    settings = _remote_settings()
    if not settings:
        return jsonify({"error": "尚未配置云端站点与登录态"}), 400
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    if not isinstance(content, str):
        return jsonify({"error": "content 必须是字符串"}), 400
    note_tags = payload.get("tags", [])
    if isinstance(note_tags, list):
        note_tags = ",".join(str(tag) for tag in note_tags)
    try:
        sync_service.make_client(settings).post_note(
            note_id, content, str(note_tags or ""), str(payload.get("folder") or ""),
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"ok": True})


@bp.delete("/remote/notes/<note_id>")
def delete_remote_note(note_id: str):
    from cloudsync import service as sync_service

    settings = _remote_settings()
    if not settings:
        return jsonify({"error": "尚未配置云端站点与登录态"}), 400
    try:
        sync_service.make_client(settings).delete_note(note_id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"ok": True})


@bp.get("/workspace/paths")
def workspace_paths():
    """返回工作区目录配置及当前文件数量。"""
    from cloudsync import settings as sync_settings
    from . import workspace

    settings = sync_settings.load_settings()
    local = workspace.local_root()
    cloud = workspace.cloud_root()
    return jsonify({
        "localDir": str(local),
        "cloudDir": str(cloud),
        "customLocal": bool(str(settings.get("local_notes_dir") or "").strip()),
        "customCloud": bool(str(settings.get("cloud_cache_dir") or "").strip()),
        "localCount": len(workspace.list_files(local)),
        "cloudCount": len(workspace.list_files(cloud)),
    })


@bp.put("/workspace/paths")
def save_workspace_paths():
    """设置本地笔记目录与云端缓存目录。"""
    from cloudsync import settings as sync_settings

    payload = request.get_json(silent=True) or {}
    current = sync_settings.load_settings()
    for key in ("local_notes_dir", "cloud_cache_dir"):
        if key in payload:
            current[key] = str(payload[key] or "").strip()
    try:
        sync_settings.save_settings(current)
    except OSError as exc:
        return jsonify({"error": f"保存失败：{exc}"}), 500
    return jsonify({"ok": True})


@bp.post("/workspace/pick-folder")
def pick_folder():
    """通过 pywebview 打开原生文件夹选择框；浏览器模式返回提示让用户输入。"""
    initial = str((request.get_json(silent=True) or {}).get("initial") or "")
    try:
        import webview

        if webview.windows:
            result = webview.windows[0].create_file_dialog(
                webview.FOLDER_DIALOG, directory=initial or None
            )
            if result:
                return jsonify({"path": result[0] if isinstance(result, (tuple, list)) else str(result)})
    except Exception:
        pass
    return jsonify({"path": "", "manual": True})


@bp.get("/workspace/local/files")
def local_files():
    from . import workspace

    return jsonify({"files": workspace.list_files(workspace.local_root())})


@bp.post("/workspace/local/sync-all")
def local_sync_all():
    """把全部本地笔记镜像到工作区目录。"""
    from app.core import note_titles
    from . import workspace

    user = _local_user()
    count = 0
    for row in _note_rows(user):
        note_id = row["id"]
        content = notes.read_note(user, note_id)
        workspace.write_file(
            workspace.local_root(), note_id, content,
            row.get("title") or note_id, row.get("folder") or "", row.get("tags") or [],
        )
        count += 1
    return jsonify({"ok": True, "count": count})


@bp.get("/workspace/cloud/files")
def cloud_files():
    from . import workspace

    return jsonify({"files": workspace.list_files(workspace.cloud_root())})


@bp.post("/workspace/cloud/pull")
def cloud_pull():
    """把云端笔记逐篇拉取为本地临时缓存（类网盘离线文件）。"""
    from cloudsync import service as sync_service
    from . import workspace

    settings = _remote_settings()
    if not settings:
        return jsonify({"error": "尚未配置云端站点与登录态"}), 400
    root = workspace.cloud_root()
    try:
        rows = sync_service.remote_note_rows(settings)
        client = sync_service.make_client(settings)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502
    ok = 0
    failed = 0
    details = []
    for row in rows:
        note_id = row["id"]
        try:
            note = client.read_note(note_id)
            workspace.write_file(
                root, note_id, note.get("content") or "",
                row.get("title") or note_id,
                note.get("folder") or row.get("folder") or "",
                row.get("tags") or [],
            )
            ok += 1
        except Exception as exc:
            failed += 1
            details.append(f"{note_id}: {exc}")
    return jsonify({"ok": ok, "failed": failed, "skipped": 0, "details": details})


@bp.get("/workspace/cloud/files/<note_id>")
def cloud_file_read(note_id: str):
    from . import workspace

    note = workspace.read_file(workspace.cloud_root(), note_id)
    if not note:
        return jsonify({"error": "本地缓存不存在，请先拉取云端笔记"}), 404
    return jsonify(note)


@bp.put("/workspace/cloud/files/<note_id>")
def cloud_file_save(note_id: str):
    """一键编辑：先写本地缓存，再推送回云端。"""
    from cloudsync import service as sync_service
    from . import workspace

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
    title = str(payload.get("title") or "")
    root = workspace.cloud_root()
    meta = workspace.write_file(root, note_id, content, title, folder, note_tags)

    settings = _remote_settings()
    pushed = False
    push_error = ""
    if settings:
        try:
            sync_service.make_client(settings).post_note(
                note_id, content, ",".join(note_tags), folder,
            )
            pushed = True
        except Exception as exc:
            push_error = str(exc)
    return jsonify({"ok": True, "pushed": pushed, "pushError": push_error, "file": meta.get("file")})


@bp.delete("/workspace/cloud/files/<note_id>")
def cloud_file_delete(note_id: str):
    """仅删除本地缓存副本，不删除云端笔记。"""
    from . import workspace

    workspace.remove_file(workspace.cloud_root(), note_id)
    return jsonify({"ok": True})


@bp.get("/sync/status")
def sync_status():
    from cloudsync import service as sync_service
    from cloudsync import settings as sync_settings

    settings = sync_settings.load_settings()
    state = sync_settings.load_state()
    configured = bool(settings.get("remote_url") and settings.get("session_cookie"))
    if configured:
        connection = {"ok": False, "message": "配置已保存；点击「测试连接」验证云端"}
    else:
        connection = {"ok": False, "message": "尚未配置云端地址与登录态"}
    if request.args.get("check") == "1" and configured:
        try:
            ok, message = sync_service.make_client(settings).check_connection()
            connection = {"ok": ok, "message": message}
        except Exception as exc:
            connection = {"message": str(exc)}
    return jsonify({
        "configured": configured,
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
