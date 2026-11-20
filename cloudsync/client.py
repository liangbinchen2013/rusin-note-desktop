"""rusin-note 网页版 HTTP 客户端：复用登录态与 CSRF，走站点原有表单路由。"""

from __future__ import annotations

import hashlib
import html
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

CSRF_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')
NOTE_LINK_RE = re.compile(r"^/user/([^/]+)/([A-Za-z0-9_-]+)$")


class SyncError(RuntimeError):
    """同步过程中可展示给用户的错误。"""


class RemoteClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        session_cookie: str = "",
        timeout: int = 20,
        delay: float = 0.3,
    ) -> None:
        parsed = urlparse((base_url or "").strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise SyncError("云端地址无效，请填写完整地址，例如 https://note.example.com")
        self.base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        self.username = (username or "").strip()
        self.timeout = timeout
        self.delay = max(0.0, float(delay))
        self.session_cookie = (session_cookie or "").strip()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "rusin-note-local-sync/0.1"})
        self.session.hooks["response"].append(self._unsecure_cookies)
        if self.session_cookie:
            self.session.cookies.set(
                "rusin_session", self.session_cookie,
                domain=parsed.hostname, path="/",
            )

    def _unsecure_cookies(self, response, *_args, **_kwargs):
        # 云端若开了 secure_cookies 又用 http 访问，requests 不会回传 Secure Cookie
        for jar in (response.cookies, self.session.cookies):
            for cookie in jar:
                try:
                    cookie.secure = False
                except Exception:
                    pass
        return response

    def _request(self, method: str, path: str, **kwargs):
        if self.delay:
            time.sleep(self.delay)
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("allow_redirects", False)
        response = self.session.request(method, urljoin(self.base + "/", path.lstrip("/")), **kwargs)
        if response.status_code == 429:
            raise SyncError("云端触发限流（429），请稍后再同步")
        return response

    def check_connection(self) -> tuple[bool, str]:
        if not self.username:
            return False, "请先填写云端用户名"
        if not self.session_cookie:
            return False, "请先填写云端站点的 rusin_session Cookie"
        response = self._request("GET", f"/user/{self.username}/")
        if response.status_code == 200:
            return True, "连接正常，登录态有效"
        if response.status_code in (401, 302, 403):
            return False, "登录态无效或已过期，请重新获取 rusin_session Cookie"
        return False, f"连接失败：HTTP {response.status_code}"

    def _csrf(self, path: str) -> str:
        response = self._request("GET", path)
        if response.status_code != 200:
            raise SyncError(f"无法读取 {path}（HTTP {response.status_code}），请检查登录态")
        match = CSRF_RE.search(response.text)
        if not match:
            raise SyncError(f"{path} 页面缺少 csrf_token，可能登录态已失效")
        return match.group(1)

    def list_remote_notes(self) -> list[str]:
        response = self._request("GET", f"/user/{self.username}/")
        if response.status_code != 200:
            raise SyncError(f"读取云端笔记列表失败（HTTP {response.status_code}）")
        soup = BeautifulSoup(response.text, "html.parser")
        found: list[str] = []
        for link in soup.find_all("a", href=True):
            match = NOTE_LINK_RE.match(link["href"])
            if match and match.group(1) == self.username and match.group(2) not in found:
                found.append(match.group(2))
        return found

    def read_note(self, note_id: str) -> dict:
        response = self._request("GET", f"/user/{self.username}/{note_id}")
        if response.status_code != 200:
            raise SyncError(f"读取云端笔记 {note_id} 失败（HTTP {response.status_code}）")
        soup = BeautifulSoup(response.text, "html.parser")
        content_node = soup.select_one("textarea[name=content]")
        if content_node is None:
            raise SyncError(f"云端笔记 {note_id} 页面没有正文编辑器")
        tags_node = soup.select_one("input[name=tags]")
        folder_node = soup.select_one("input[name=folder]")
        return {
            "id": note_id,
            "content": content_node.get_text(),
            "tags": tags_node.get("value", "") if tags_node else "",
            "folder": folder_node.get("value", "") if folder_node else "",
        }

    def post_note(self, note_id: str, content: str, tags: str = "", folder: str = "") -> bool:
        csrf = self._csrf(f"/user/{self.username}/{note_id}")
        response = self._request(
            "POST",
            f"/user/{self.username}/{note_id}",
            data={
                "csrf_token": csrf,
                "content": content,
                "tags": tags or "",
                "folder": folder or "",
            },
            headers={"Referer": urljoin(self.base, f"/user/{self.username}/{note_id}")},
        )
        if response.status_code == 302:
            return True
        if response.status_code == 400:
            try:
                message = response.json().get("error", "")
            except ValueError:
                message = "表单校验失败"
            raise SyncError(f"推送笔记 {note_id} 失败：{message or '表单校验失败'}")
        raise SyncError(f"推送笔记 {note_id} 失败：HTTP {response.status_code}")

    def create_note(self, folder: str = "") -> str:
        """在云端新建笔记，返回云端分配的笔记 ID。"""
        response = self._request("GET", f"/user/{self.username}/new")
        if response.status_code != 302:
            raise SyncError(f"云端新建笔记失败（HTTP {response.status_code}）")
        location = response.headers.get("Location", "")
        match = re.search(rf"/user/{re.escape(self.username)}/([A-Za-z0-9_-]+)", location)
        if not match:
            raise SyncError(f"无法从云端响应解析笔记 ID：{location}")
        note_id = match.group(1)
        self.post_note(note_id, "\n", "", folder)
        return note_id

    def delete_note(self, note_id: str) -> bool:
        """云端空内容保存即删除（会级联清理标签/文件夹/分享）。"""
        path = f"/user/{self.username}/{note_id}"
        csrf = self._csrf(path)
        response = self._request(
            "POST", path,
            data={"csrf_token": csrf, "content": ""},
            headers={"Referer": urljoin(self.base, path)},
        )
        if response.status_code == 302:
            return True
        raise SyncError(f"删除云端笔记 {note_id} 失败：HTTP {response.status_code}")

    def list_benben(self, max_pages: int = 1) -> list[dict]:
        posts: list[dict] = []
        for page in range(1, max(1, int(max_pages)) + 1):
            response = self._request("GET", f"/benben?page={page}")
            if response.status_code != 200:
                raise SyncError(f"读取云端犇犇第 {page} 页失败（HTTP {response.status_code}）")
            soup = BeautifulSoup(response.text, "html.parser")
            nodes = soup.select("div.benben-post")
            if not nodes:
                break
            for node in nodes:
                meta = node.select_one(".benben-meta")
                time_node = node.select_one(".benben-time")
                body = node.select_one(".benben-body")
                if meta is None or body is None:
                    continue
                time_str = time_node.get_text(strip=True) if time_node else ""
                username = meta.get_text(strip=True).replace(time_str, "").strip()
                content = html.unescape(body.get_text(" ", strip=True))
                signature = hashlib.sha256(
                    f"{username}|{time_str}|{content}".encode("utf-8")
                ).hexdigest()
                posts.append({
                    "username": username,
                    "time_str": time_str,
                    "content": content,
                    "signature": signature,
                })
        return posts

    def post_benben(self, content: str) -> bool:
        csrf = self._csrf("/benben")
        response = self._request(
            "POST", "/benben",
            data={"csrf_token": csrf, "content": content},
            headers={"Referer": urljoin(self.base, "/benben")},
        )
        if response.status_code == 302:
            return True
        raise SyncError(f"推送犇犇失败：HTTP {response.status_code}（可能触发冷却或内容超长）")
