"""托管 React/Vite 构建产物，让应用启动时直接进入 IDE 界面。"""

from pathlib import Path

from flask import Blueprint, send_from_directory

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "dist"

bp = Blueprint("ide_web", __name__)


@bp.route("/")
def index():
    index_file = DIST / "index.html"
    if not index_file.is_file():
        return (
            "<h1>前端尚未构建</h1><p>请在 web/ 目录执行 npm install && npm run build</p>",
            503,
        )
    return send_from_directory(DIST, "index.html")


@bp.route("/assets/<path:filename>")
def assets(filename: str):
    return send_from_directory(DIST / "assets", filename)


@bp.route("/favicon.svg")
def favicon():
    return send_from_directory(DIST, "favicon.svg")


@bp.route("/logo.png")
def logo():
    return send_from_directory(DIST, "logo.png")
