"""本地优先的 rusin-note 应用入口。

启动一个只监听 127.0.0.1 的本地服务，再用原生窗口（pywebview）打开；
窗口不可用时回退到系统浏览器。开发模式数据在工作区 data/，打包后
数据落在使用者目录（Windows 为 %APPDATA%\\rusin-note-local）。
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
# 冻结后资源在 sys._MEIPASS 临时解压目录；源码模式就在项目根
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

if FROZEN:
    if os.name == "nt":
        default_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "rusin-note-local"
    elif sys.platform == "darwin":
        default_data = Path.home() / "Library" / "Application Support" / "rusin-note-local"
    else:
        default_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "rusin-note-local"
else:
    default_data = RESOURCE_ROOT / "data"

DATA_DIR = Path(os.environ.get("RUSIN_DESKTOP_DATA_DIR", str(default_data))).expanduser()
# 应用的 config.json 按当前工作目录解析，冻结后也要切到资源根
os.chdir(RESOURCE_ROOT)
os.environ.setdefault("RUSIN_DATA_DIR", str(DATA_DIR))
os.environ.setdefault("RUSIN_STORAGE", "sqlite")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_server(port: int):
    from app import create_app
    from waitress import create_server

    return create_server(create_app(), host="127.0.0.1", port=port, threads=8)


class DesktopApi:
    """暴露给前端 WebView 的原生能力（文件夹选择等）。"""

    def pickFolder(self, initial: str = ""):
        try:
            import webview

            if not webview.windows:
                return {"path": "", "manual": True}
            result = webview.windows[0].create_file_dialog(
                webview.FOLDER_DIALOG, directory=initial or None
            )
            if result:
                path = result[0] if isinstance(result, (tuple, list)) else str(result)
                return {"path": path}
        except Exception:
            pass
        return {"path": "", "manual": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="如形本地笔记")
    parser.add_argument("--browser", action="store_true", help="用系统浏览器代替原生窗口")
    parser.add_argument("--port", type=int, default=0, help="固定端口（默认自动选择空闲端口）")
    args = parser.parse_args()

    port = args.port or free_port()
    url = f"http://127.0.0.1:{port}/"
    server = build_server(port)
    thread = threading.Thread(target=server.run, name="rusin-local-server", daemon=True)
    thread.start()

    print(f"本地服务已启动：{url}")
    print(f"笔记数据目录：{DATA_DIR}")

    opened_window = False
    if not args.browser:
        try:
            import webview

            storage_path = DATA_DIR / "webview"
            storage_path.mkdir(parents=True, exist_ok=True)
            window = webview.create_window(
                "如形本地笔记 · IDE", url=url, width=1440, height=900,
                min_size=(1024, 680), maximized=True, js_api=DesktopApi(),
            )
            webview.start(private_mode=False, storage_path=str(storage_path))
            opened_window = True
        except Exception as exc:  # 无桌面运行时/依赖时优雅降级
            print(f"无法启动原生窗口（{exc}），改用系统浏览器。", file=sys.stderr)

    if not opened_window:
        webbrowser.open(url)
        try:
            while thread.is_alive():
                thread.join(timeout=1)
        except KeyboardInterrupt:
            print("\n正在退出…")

    server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
