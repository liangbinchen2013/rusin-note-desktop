# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：由 release/build.py 通过 RUSIN_BUILD_* 环境变量驱动。

注意：本文件在 .gitignore 中被显式放行，请随项目一起提交。
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# SPECPATH 是 PyInstaller 执行 spec 时注入的变量，指向 spec 所在目录（release/）
ROOT_DIR = Path(SPECPATH).parent.resolve()

SLIM = os.environ.get("RUSIN_BUILD_SLIM", "1") == "1"
ONEDIR = os.environ.get("RUSIN_BUILD_ONEDIR", "0") == "1"
CONSOLE = os.environ.get("RUSIN_BUILD_CONSOLE", "0") == "1"


def _slash(path: Path) -> str:
    """PyInstaller 的 datas 统一用正斜杠，避免 Windows 反斜杠被当作转义。"""
    return str(path).replace("\\", "/")


# 程序运行时会 chdir 到 _MEIPASS，因此这些资源都放到解压根目录
# 注意：PyInstaller 会把相对路径按 spec 所在目录（release/）解析，
# 因此源路径一律使用基于 ROOT_DIR 的绝对路径。
datas = [
    (_slash(ROOT_DIR / "config.json"), "."),
    (_slash(ROOT_DIR / "NOTICE.txt"), "."),
    (_slash(ROOT_DIR / "templates"), "templates"),
    (_slash(ROOT_DIR / "web" / "dist"), "web/dist"),
]

static_root = ROOT_DIR / "app" / "static"

if SLIM:
    # 旧 Jinja 页面专用的大资源（vditor / fontawesome）不进入 IDE 版
    skip_parts = {"vditor", "fontawesome"}
    for item in static_root.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(static_root)
        if any(part in skip_parts for part in rel.parts):
            continue
        datas.append((_slash(item), _slash(Path("app/static") / rel)))
else:
    datas.append((_slash(static_root), "app/static"))

# registry.py 等模块虽然是静态导入，仍显式收集以防漏掉插件/平台后端
hiddenimports = []
for package in ("app", "cloudsync", "ideapi", "webview"):
    hiddenimports.extend(collect_submodules(package))

# slim 模式排除本地 IDE 用不到的重依赖；config.json 的 cache.enabled 为 false
excludes = ["psycopg", "redis", "PIL", "mangum"] if SLIM else []

a = Analysis(
    [_slash(ROOT_DIR / "main.py")],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

if ONEDIR:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="rusin-note-ide",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=CONSOLE,
        icon=_slash(ROOT_DIR / "release" / "app.ico"),
    )
    coll = COLLECT(
        exe, a.binaries, a.datas,
        strip=False,
        upx=True,
        name="rusin-note-ide",
    )
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="rusin-note-ide",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=CONSOLE,
        icon=_slash(ROOT_DIR / "release" / "app.ico"),
    )
