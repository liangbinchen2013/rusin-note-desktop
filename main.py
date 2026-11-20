"""本地优先的 rusin-note 应用入口。

启动一个只监听 127.0.0.1 的本地服务，再用原生窗口（pywebview）打开；
窗口不可用时回退到系统浏览器。笔记数据保存在工作区 data/ 目录。
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# 应用的 config.json / data 都按当前工作目录解析，必须先切到项目根
os.chdir(ROOT)
os.environ.setdefault("RUSIN_DATA_DIR", str(ROOT / "data"))
os.environ.setdefault("RUSIN_STORAGE", "sqlite")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_server(port: int):
    from app import create_app
    from waitress import create_server

    return create_server(create_app(), host="127.0.0.1", port=port, threads=8)


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
    print("按 Ctrl+C 退出；笔记数据保存在 data/ 目录。")

    opened_window = False
    if not args.browser:
        try:
            import webview

            storage_path = ROOT / "data" / "webview"
            storage_path.mkdir(parents=True, exist_ok=True)
            window = webview.create_window(
                "如形本地笔记", url=url, width=1280, height=860, min_size=(900, 600)
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
