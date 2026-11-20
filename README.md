# 如形本地笔记 · IDE 版

本地优先的 Markdown 笔记工作台：打开就是一个类似 IDE 的界面——活动栏、文件树、多标签编辑器、Monaco 代码编辑器、Markdown 实时预览、命令面板和状态栏。笔记全部存在本机，同时可按需与 rusin-note 云端同步（拉取犇犇/笔记、推送本地笔记）。

## 技术栈

- **外壳**：Flask 本地服务 + pywebview 原生窗口（仅监听 `127.0.0.1`），失败时回退系统浏览器
- **前端**：React 18 + Vite 6 + Monaco Editor，暗色/浅色主题
- **后端**：保留 rusin-note 的 SQLite/JSON 存储、标签、文件夹与同步逻辑；新增 `/api/ide` JSON API
- **同步**：`cloudsync/` 直接调用云端站点原有表单 POST，慢速增量，不改云端源码

## 快速开始

需要 Python 3.10+、[uv](https://docs.astral.sh/uv/)；Windows 可直接双击 `start-local.bat`。

```bash
uv sync
uv run python main.py
```

`main.py` 会自动选择空闲端口、启动本地服务并打开原生窗口（WebView2），窗口不可用时自动开浏览器。`--browser` 强制浏览器，`--port 8080` 固定端口。

前端构建产物已提交在 `web/dist/`，开箱即用。修改前端后重新构建：

```bash
cd web
npm install
npm run build
```

开发前端时可另开终端跑 `npm run dev`（默认 5173），Vite 会把 `/api` 代理到 `http://127.0.0.1:18080`。

## IDE 界面

| 区域 | 功能 |
|---|---|
| 左侧活动栏 | 资源管理器、搜索、云端同步、设置、主题切换、命令面板 |
| 资源管理器 | 按文件夹（`/` 分层）展示笔记树；新建、删除、刷新 |
| 搜索 | 按标题、ID、标签、正文全文检索，带摘要 |
| 编辑器 | 多标签页；Monaco Markdown 编辑；右侧实时预览（GFM、表格、代码高亮、KaTeX） |
| 命令面板 | `Ctrl+P` 快速打开笔记/命令；`Ctrl+Shift+P` 也可打开 |
| 状态栏 | 当前用户、云端配置状态、字数、保存状态、路径 |

快捷键：`Ctrl+S` 保存，`Ctrl+P` 命令面板。编辑后 1.5 秒自动保存；文件夹和标签在编辑器顶部直接修改。数据目录仍是工作区 `data/`，备份整个目录即可。

旧版 Jinja 页面（登录、注册、管理页等）仍保留在原路由上，但启动首页现在是 React IDE。

## 云端同步

在活动栏点云朵图标进入同步面板，填写：

- 云端地址（如 `https://note.example.com`）
- 云端用户名
- 浏览器登录云端后复制的 `rusin_session` Cookie（留空表示沿用已保存值）
- 本地用户名（只有一个本地用户时可留空）

支持：测试连接、拉取云端犇犇（按签名去重）、拉取云端笔记（保存为 `c-<ID>` 镜像）、推送本地笔记（按内容哈希增量 POST）、推送本地犇犇（间隔 3.5 秒避开冷却）、全部同步。Cookie 加密保存在 `data/sync_settings.json`，运行记录保存在 `data/sync_state.json`。

> 云端没有笔记/犇犇的 JSON API，同步按其 HTML 页面与表单实现；云端模板大改时解析逻辑可能需要更新。

## 目录

```plaintext
rusin-note-desktop/
├─ main.py                本地入口（本地服务 + WebView/浏览器）
├─ start-local.bat        Windows 双击启动
├─ config.json            本地化后的应用配置
├─ app/ templates/        上游 Flask 应用与模板（兼容保留）
├─ ideapi/                本地 IDE JSON API + 前端托管
├─ cloudsync/             云端同步模块
├─ web/                   React + Vite + Monaco 前端；dist/ 为构建产物
├─ data/                  运行时数据（git 忽略）
└─ tests/                 后端 / API / 同步测试
```

## 测试

```bash
uv run pytest tests/ -q
```

测试使用临时数据目录，不触碰真实的 `data/`。
