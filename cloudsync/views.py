"""云端同步设置与操作页面。"""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.core.middleware import get_current_user

from . import settings as settings_store

bp = Blueprint("cloud_sync", __name__, url_prefix="/sync")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not get_current_user():
            return redirect("/login")
        return view(*args, **kwargs)
    return wrapped


@bp.route("/", methods=["GET"])
@login_required
def index():
    from . import service  # 延迟导入，避免与 app 初始化互相 import

    settings = settings_store.load_settings()
    state = settings_store.load_state()
    ok, message = service.make_client(settings).check_connection() if (
        settings.get("remote_url") and settings.get("session_cookie")
    ) else (False, "尚未配置云端地址与登录态")
    return render_template(
        "sync/index.html",
        full_title="云端同步",
        settings=settings,
        users=service.local_users(),
        connection_ok=ok,
        connection_message=message,
        runs=state["runs"],
        stats={
            "pushed_notes": len(state["notes"]),
            "pulled_notes": len(state["remote_notes"]),
            "benben_seen": len(state["benben_seen"]),
        },
    )


@bp.route("/settings", methods=["POST"])
@login_required
def save_settings():
    payload = {
        "remote_url": request.form.get("remote_url", "").strip().rstrip("/"),
        "remote_user": request.form.get("remote_user", "").strip(),
        "session_cookie": request.form.get("session_cookie", "").strip(),
        "local_user": request.form.get("local_user", "").strip(),
        "overwrite_remote": "overwrite_remote" in request.form,
        "overwrite_local": "overwrite_local" in request.form,
        "pull_pages": request.form.get("pull_pages", "1") or "1",
        "request_delay": request.form.get("request_delay", "0.3") or "0.3",
    }
    if payload["remote_url"] and "://" not in payload["remote_url"]:
        local_host = payload["remote_url"].startswith(("localhost", "127.0.0.1"))
        payload["remote_url"] = ("http://" if local_host else "https://") + payload["remote_url"]
    current = settings_store.load_settings()
    if not payload["session_cookie"]:
        payload["session_cookie"] = current.get("session_cookie", "")
    try:
        settings_store.save_settings(payload)
    except OSError as exc:
        flash(f"保存设置失败：{exc}", "error")
    else:
        flash("同步设置已保存到本地 data/ 目录（Cookie 已加密）", "ok")
    return redirect(url_for("cloud_sync.index"))


@bp.route("/action/<name>", methods=["POST"])
@login_required
def action(name: str):
    from . import service  # 延迟导入，避免与 app 初始化互相 import

    handlers = {
        "test": service.test_connection,
        "pull_benben": service.pull_benben,
        "pull_notes": service.pull_notes,
        "push_notes": service.push_notes,
        "push_benben": service.push_benben,
        "sync_all": service.sync_all,
    }
    handler = handlers.get(name)
    if handler is None:
        abort(404)
    settings = settings_store.load_settings()
    try:
        report = handler(settings)
    except Exception as exc:  # 同步不允许把本地应用打崩
        report = {"ok": 0, "skipped": 0, "failed": 1, "details": [f"未预期错误：{exc}"]}
    settings_store.record_run(name, report)
    for line in report.get("details", [])[:20]:
        flash(line, "ok" if report["failed"] == 0 else "error")
    flash(
        f"操作完成：成功 {report['ok']} / 跳过 {report['skipped']} / 失败 {report['failed']}",
        "ok" if report["failed"] == 0 else "error",
    )
    return redirect(url_for("cloud_sync.index"))
