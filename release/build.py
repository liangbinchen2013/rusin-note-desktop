"""打包本地 IDE 为 exe：默认单文件 + 精简资源。"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "release" / "rusin-note-ide.spec"


def human(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main() -> int:
    parser = argparse.ArgumentParser(description="打包 rusin-note IDE")
    parser.add_argument("--full", action="store_true", help="包含旧版前端大资源（体积更大）")
    parser.add_argument("--onedir", action="store_true", help="打包为目录而非单文件（启动更快）")
    parser.add_argument("--console", action="store_true", help="保留控制台窗口，便于排障")
    args = parser.parse_args()

    if not (ROOT / "web" / "dist" / "index.html").is_file():
        print("前端尚未构建，请先执行：cd web && npm install && npm run build", file=sys.stderr)
        return 1

    dist = ROOT / "dist"
    env = os.environ.copy()
    env["RUSIN_BUILD_SLIM"] = "0" if args.full else "1"
    env["RUSIN_BUILD_ONEDIR"] = "1" if args.onedir else "0"
    env["RUSIN_BUILD_CONSOLE"] = "1" if args.console else "0"

    # PyInstaller 会尝试删除旧 exe；Windows 上旧文件可能被预览/杀软锁定，先改名更稳
    old_exe = dist / ("rusin-note-ide.exe" if os.name == "nt" else "rusin-note-ide")
    if old_exe.exists():
        old_exe.rename(dist / f"rusin-note-ide-prev-{int(time.time())}{old_exe.suffix}")

    print("开始打包…（单文件模式首次解压较慢，属正常现象）")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(SPEC)],
        cwd=ROOT, env=env, check=True,
    )

    if args.onedir:
        target = dist / "rusin-note-ide" / ("rusin-note-ide.exe" if os.name == "nt" else "rusin-note-ide")
        size = sum(p.stat().st_size for p in (dist / "rusin-note-ide").rglob("*") if p.is_file())
    else:
        suffix = ".exe" if os.name == "nt" else ""
        target = dist / f"rusin-note-ide{suffix}"
        size = target.stat().st_size if target.exists() else 0

    print(f"打包完成：{target}")
    print(f"产物体积：{human(size)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
