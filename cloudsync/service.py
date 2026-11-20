"""同步编排：本地 SQLite 笔记与云端站点之间的拉取 / 推送。"""

from __future__ import annotations

import hashlib
import time

from app.core import folders as local_folders
from app.core import notes as local_notes
from app.core import store as local_store
from app.core import tags as local_tags

from .client import RemoteClient, SyncError
from . import settings as settings_store


def digest(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def local_users() -> list[str]:
    with local_store.users_lock:
        return sorted(local_store.users.keys())


def resolve_local_user(settings: dict) -> str:
    candidate = (settings.get("local_user") or "").strip()
    users = local_users()
    if candidate:
        if candidate not in users:
            raise SyncError(f"本地用户 {candidate} 不存在")
        return candidate
    if len(users) == 1:
        return users[0]
    raise SyncError("本地存在多个用户，请在同步设置中指定要同步的本地用户名")


def make_client(settings: dict) -> RemoteClient:
    return RemoteClient(
        settings.get("remote_url", ""),
        settings.get("remote_user", ""),
        settings.get("session_cookie", ""),
        delay=float(settings.get("request_delay", 0.3) or 0),
    )


def test_connection(settings: dict) -> dict:
    ok, message = make_client(settings).check_connection()
    return {"ok": 1 if ok else 0, "failed": 0 if ok else 1, "details": [message]}


def push_notes(settings: dict, force: bool = False) -> dict:
    """把本地笔记 POST 到云端；内容未变化则跳过（慢速增量同步）。"""
    user = resolve_local_user(settings)
    state = settings_store.load_state()
    client = make_client(settings)
    report = {"ok": 0, "skipped": 0, "failed": 0, "details": []}
    remote_url = (settings.get("remote_url") or "").rstrip("/")

    for meta in local_notes.list_user_notes_detailed(user):
        note_id = meta["id"]
        content = local_notes.read_note(user, note_id)
        if not content:
            continue
        current_hash = digest(content)
        previous = state["notes"].get(note_id, {})
        if (
            not force
            and previous.get("hash") == current_hash
            and previous.get("remote_url") == remote_url
        ):
            report["skipped"] += 1
            continue
        try:
            client.post_note(
                note_id,
                content,
                ",".join(local_tags.get_note_tags(user, note_id)),
                local_folders.get_note_folder(user, note_id),
            )
        except SyncError as exc:
            report["failed"] += 1
            report["details"].append(f"{note_id}: {exc}")
            continue
        state["notes"][note_id] = {
            "hash": current_hash,
            "pushed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "remote_url": remote_url,
        }
        report["ok"] += 1
        report["details"].append(f"{note_id}: 已推送")

    settings_store.save_state(state)
    return report


def pull_benben(settings: dict) -> dict:
    """拉取云端犇犇到本地动态流，按内容签名去重。"""
    client = make_client(settings)
    state = settings_store.load_state()
    seen = set(state["benben_seen"])
    report = {"ok": 0, "skipped": 0, "failed": 0, "details": []}
    try:
        posts = client.list_benben(int(settings.get("pull_pages", 1) or 1))
    except SyncError as exc:
        report["failed"] += 1
        report["details"].append(str(exc))
        return report

    for post in reversed(posts):  # 旧帖先落库，页面按时间倒序展示
        if post["signature"] in seen:
            report["skipped"] += 1
            continue
        local_store.add_benben_post(post["username"], post["content"], ip="cloud-sync")
        seen.add(post["signature"])
        report["ok"] += 1
    state["benben_seen"] = list(seen)[-2000:]
    settings_store.save_state(state)
    report["details"].append(f"云端共读取 {len(posts)} 条，新增 {report['ok']} 条")
    return report


def pull_notes(settings: dict) -> dict:
    """把云端笔记镜像到本地，使用 c- 前缀避免覆盖本地笔记。"""
    user = resolve_local_user(settings)
    client = make_client(settings)
    state = settings_store.load_state()
    report = {"ok": 0, "skipped": 0, "failed": 0, "details": []}
    try:
        remote_ids = client.list_remote_notes()
    except SyncError as exc:
        report["failed"] += 1
        report["details"].append(str(exc))
        return report

    for note_id in remote_ids:
        try:
            remote = client.read_note(note_id)
        except SyncError as exc:
            report["failed"] += 1
            report["details"].append(str(exc))
            continue
        current_hash = digest(remote["content"])
        previous = state["remote_notes"].get(note_id, {})
        if previous.get("hash") == current_hash:
            report["skipped"] += 1
            continue
        local_id = f"c-{note_id}"
        if local_notes.note_exists(user, local_id) and not settings.get("overwrite_local", True):
            report["skipped"] += 1
            report["details"].append(f"{note_id}: 本地镜像有改动，已跳过")
            continue
        if not local_notes.write_note(user, local_id, remote["content"]):
            report["failed"] += 1
            report["details"].append(f"{note_id}: 写入本地失败")
            continue
        if remote["tags"]:
            local_tags.set_note_tags(user, local_id, [t.strip() for t in remote["tags"].split(",") if t.strip()])
        if remote["folder"]:
            local_folders.set_note_folder(user, local_id, remote["folder"])
        state["remote_notes"][note_id] = {
            "hash": current_hash,
            "pulled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        report["ok"] += 1
        report["details"].append(f"{note_id} → {local_id}: 已拉取")

    settings_store.save_state(state)
    return report


def push_benben(settings: dict) -> dict:
    """把本地用户发布的犇犇推送到云端（每条约 3.5 秒，避开云端冷却）。"""
    user = resolve_local_user(settings)
    client = make_client(settings)
    state = settings_store.load_state()
    pushed = set(state["pushed_benben"])
    report = {"ok": 0, "skipped": 0, "failed": 0, "details": []}
    posts, _ = local_store.get_benben_posts(1, 200)
    mine = [p for p in reversed(posts) if p.get("username") == user]
    for post in mine:
        signature = digest(post.get("content", ""))
        if signature in pushed:
            report["skipped"] += 1
            continue
        try:
            client.post_benben(post.get("content", ""))
        except SyncError as exc:
            report["failed"] += 1
            report["details"].append(str(exc))
            break
        pushed.add(signature)
        report["ok"] += 1
        report["details"].append("犇犇已推送")
        if len(report["details"]) and report["ok"] < len(mine):
            time.sleep(3.5)  # 云端默认 3 秒冷却
    state["pushed_benben"] = list(pushed)[-500:]
    settings_store.save_state(state)
    return report


def sync_all(settings: dict) -> dict:
    total = {"ok": 0, "skipped": 0, "failed": 0, "details": []}
    for label, func in (
        ("拉取犇犇", pull_benben),
        ("拉取云端笔记", pull_notes),
        ("推送本地笔记", push_notes),
    ):
        try:
            part = func(settings)
        except SyncError as exc:
            part = {"ok": 0, "skipped": 0, "failed": 1, "details": [str(exc)]}
        for key in ("ok", "skipped", "failed"):
            total[key] += part[key]
        total["details"].append(f"[{label}] " + "；".join(part["details"]) or f"[{label}] 完成")
    return total
