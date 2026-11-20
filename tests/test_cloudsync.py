from cloudsync import service, settings as sync_settings
from app.core import notes as local_notes
from app.core import store


class FakeClient:
    def __init__(self):
        self.pushed = []
        self.remote_posts = []
        self.remote_notes = {}

    def post_note(self, note_id, content, tags="", folder=""):
        self.pushed.append((note_id, content, tags, folder))
        return True

    def list_benben(self, max_pages=1):
        return self.remote_posts

    def list_remote_notes(self):
        return list(self.remote_notes)

    def read_note(self, note_id):
        return self.remote_notes[note_id]


def make_user(name: str = "syncuser") -> str:
    store.register_user(name, {"salt": "x", "hash": "y"})
    return name


def test_settings_encrypt_cookie():
    sync_settings.save_settings({
        "remote_url": "https://note.example.com",
        "remote_user": "alice",
        "session_cookie": "supersecret-cookie",
        "local_user": "syncuser",
    })
    raw = sync_settings._settings_path().read_text(encoding="utf-8")
    assert "supersecret-cookie" not in raw
    assert sync_settings.load_settings()["session_cookie"] == "supersecret-cookie"


def test_push_notes_is_incremental(monkeypatch):
    user = make_user("pushuser")
    local_notes.write_note(user, "push001", "# 本地笔记\n内容")
    fake = FakeClient()
    monkeypatch.setattr(service, "make_client", lambda settings: fake)
    settings = {"remote_url": "https://note.example.com", "local_user": user}

    first = service.push_notes(settings)
    second = service.push_notes(settings)

    assert first["ok"] == 1 and second["skipped"] == 1
    assert len(fake.pushed) == 1
    assert fake.pushed[0][0] == "push001"
    assert "本地笔记" in fake.pushed[0][1]


def test_pull_benben_dedupe(monkeypatch):
    fake = FakeClient()
    fake.remote_posts = [
        {"username": "alice", "time_str": "刚刚", "content": "云端动态 A", "signature": "sig-a"},
        {"username": "bob", "time_str": "1 分钟前", "content": "云端动态 B", "signature": "sig-b"},
    ]
    monkeypatch.setattr(service, "make_client", lambda settings: fake)
    settings = {"remote_url": "https://note.example.com"}

    first = service.pull_benben(settings)
    second = service.pull_benben(settings)
    posts, _ = store.get_benben_posts(1, 50)
    contents = [p["content"] for p in posts]

    assert first["ok"] == 2 and second["skipped"] == 2
    assert "云端动态 A" in contents and "云端动态 B" in contents


def test_pull_notes_uses_prefix(monkeypatch):
    user = make_user("pulluser")
    fake = FakeClient()
    fake.remote_notes = {
        "abcd": {
            "id": "abcd",
            "content": "# 云端笔记\n同步内容",
            "tags": "云,同步",
            "folder": "云端",
        }
    }
    monkeypatch.setattr(service, "make_client", lambda settings: fake)

    report = service.pull_notes({"local_user": user})

    assert report["ok"] == 1
    assert "同步内容" in local_notes.read_note(user, "c-abcd")
    assert "云端" in local_notes.read_note(user, "c-abcd")
