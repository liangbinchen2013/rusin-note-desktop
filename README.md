# 如形本地笔记（rusin-note-local）

本地优先的笔记应用：笔记、犇犇、附件都落在自己的电脑，同时可以**拉取云端犇犇/笔记**、**把本地笔记推送到 rusin-note 网页版**。云端同步直接调用站点原有的表单 POST，慢速增量执行，不需要修改云端源码。

## 它和上游 rusin-note 的关系

- 基础是 `rusin-note` 仓库的 Flask 网页版（`app/`、`templates/`、`config.json`），完整保留笔记、Markdown、标签、文件夹、图床、附件、犇犇、组织等能力。
- 本地化改动：
  - `config.json` 关闭注册验证码、Redis 缓存、插件和对外下载页；放宽限流；关闭 Secure Cookie（本地是 `http://127.0.0.1`）。
  - 修复 Flask-Caching 2.x 下 `CACHE_TYPE: "null"` 无法导入的问题。
  - 新增 `cloudsync/` 同步模块与 `/sync` 页面；`main.py` 启动本地服务并打开原生窗口。
- 上游仓库 `C:/Users/ALIENWARE/Desktop/rusin-note` 未被修改。

## 快速开始

需要 Python 3.10+ 与 [uv](https://docs.astral.sh/uv/)。Windows 上直接双击 `start-local.bat`，或命令行：

```bash
uv sync
uv run python main.py
```

`main.py` 会选择一个空闲端口，只监听 `127.0.0.1`，然后：

- 优先用 pywebview 打开原生窗口（Windows 需要 WebView2 运行时，Win10/11 通常已预装）；
- 原生窗口不可用时自动回退到系统浏览器；
- `uv run python main.py --browser` 可强制使用浏览器；`--port 8080` 可固定端口。

首次打开按页面提示注册本地账号即可。所有数据在工作区的 `data/` 目录（已加入 `.gitignore`），备份时复制整个目录；想彻底重置就删掉它（会丢失全部本地笔记）。

## 云端同步

打开左侧栏（或导航栏）的 **云端同步**，填入：

| 字段 | 说明 |
|---|---|
| 云端地址 | 你的 rusin-note 站点根地址，如 `https://note.example.com` |
| 云端用户名 | 该站点上要同步的账号 |
| 登录 Cookie | 浏览器登录站点后，从开发者工具复制 `rusin_session` 的值 |
| 本地用户名 | 要同步的本地账号；只有一个本地用户时可留空自动识别 |

 Cookie 用本地生成的密钥加密后保存在 `data/sync_settings.json`，**等同于云端登录态，不要分享该文件**。云端若使用了验证码/2FA，从浏览器里复制现成的 Cookie 是最省事的方式。

可用操作：

- **测试连接**：验证 Cookie 是否有效。
- **拉取云端犇犇**：读取站点 `/benben` 前 N 页，按「用户名 + 时间 + 正文」签名去重后写入本地犇犇流。
- **拉取云端笔记**：把云端笔记镜像为本地 `c-<原ID>` 笔记，不会覆盖本地同名笔记；内容变化时更新镜像。
- **推送本地笔记**：逐篇把本地笔记 POST 到云端 `/user/<用户名>/<笔记ID>`，同时带上标签和文件夹。按内容哈希做增量同步，未改动自动跳过；可选「允许覆盖云端同名笔记」。
- **推送本地犇犇**：把本地账号发布的动态发到云端，间隔 3.5 秒以避开云端 3 秒冷却。
- **全部同步**：依次执行拉取犇犇、拉取云端笔记、推送本地笔记。

同步是手动触发的，不做后台轮询；每次操作的结果与详情保存在 `data/sync_state.json`，页面上能看到最近 20 条记录。请求间隔默认 0.3 秒，可在设置里调大以进一步降低对云端的压力。

> 云端站点目前没有笔记/犇犇的 JSON API，客户端按其 HTML 表单与页面结构实现；如果云端模板大改，解析可能需要同步更新。云端触发限流（429）时会停止并给出提示，稍后重试即可。

## 目录

```plaintext
rusin-note-desktop/
├─ main.py               本地入口（本地服务 + WebView/浏览器）
├─ start-local.bat       Windows 双击启动
├─ config.json           本地化后的应用配置
├─ app/ templates/       上游 Flask 应用与模板
├─ cloudsync/            同步模块（settings / client / service / views）
├─ data/                 运行时数据（笔记、SQLite 索引、同步配置与状态）
└─ tests/                同步模块单元测试
```

## 测试

```bash
uv run pytest tests/ -q
```

测试会在临时数据目录中运行，不触碰 `data/`。
