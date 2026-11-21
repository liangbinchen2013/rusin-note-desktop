"""笔记自定义标题存储：与正文分离，存通用 KV 键 note_titles。

结构：{username: {note_id: title}}。标题是 IDE 里用户可编辑的显示名，
留空时回退为正文首行。写路径与 tags.py / folders.py 一致：进程内 Lock
+ storage.lock 跨实例重读合并，持久化在锁外执行。
"""
import threading

from app.core.logger import create_logger
from app.core.storage import StorageError, storage

logger = create_logger("note_titles")

K_TITLES = "note_titles"
MAX_TITLE_LENGTH = 200

note_titles = {}  # {username: {note_id: title}}
titles_lock = threading.Lock()


def _persist(data: dict) -> bool:
    try:
        return storage.set(K_TITLES, data)
    except StorageError as e:
        logger.error(f"[错误] 存储写入 {K_TITLES} 失败: {e}")
        return False


def _read() -> dict | None:
    try:
        value = storage.get(K_TITLES)
    except StorageError as e:
        logger.error(f"[错误] 存储读取 {K_TITLES} 失败: {e}")
        return None
    return value if isinstance(value, dict) else None


def _read_merge_locked():
    data = _read()
    if isinstance(data, dict):
        note_titles.clear()
        note_titles.update(data)


def load_note_titles():
    with titles_lock:
        data = _read()
        if isinstance(data, dict):
            note_titles.clear()
            note_titles.update(data)


def clean_title(raw: str) -> str:
    """规范化标题：去首尾空白、折叠空白、截断长度。"""
    text = " ".join(str(raw or "").split())
    return text[:MAX_TITLE_LENGTH]


def get_user_note_titles(username: str) -> dict:
    with titles_lock:
        user = note_titles.get(username)
        return {nid: t for nid, t in user.items()} if isinstance(user, dict) else {}


def get_note_title(username: str, note_id: str) -> str:
    with titles_lock:
        user = note_titles.get(username)
        if not isinstance(user, dict):
            return ""
        title = user.get(note_id)
        return title if isinstance(title, str) else ""


def set_note_title(username: str, note_id: str, title: str) -> bool:
    clean = clean_title(title)
    try:
        with titles_lock:
            with storage.lock(K_TITLES):
                _read_merge_locked()
                user = note_titles.get(username)
                if clean:
                    if not isinstance(user, dict):
                        user = {}
                        note_titles[username] = user
                    user[note_id] = clean
                elif isinstance(user, dict):
                    user.pop(note_id, None)
                    if not user:
                        note_titles.pop(username, None)
                return _persist(note_titles)
    except StorageError as e:
        logger.error(f"[错误] 写入笔记标题 {username}/{note_id} 失败: {e}")
        return False


def delete_note_title(username: str, note_id: str) -> bool:
    return set_note_title(username, note_id, "")


load_note_titles()
