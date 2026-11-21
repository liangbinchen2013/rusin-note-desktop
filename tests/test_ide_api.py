def _client():
    from app import create_app
    return create_app().test_client()


def test_bootstrap_and_note_crud():
    client = _client()
    boot = client.get('/api/ide/bootstrap')
    assert boot.status_code == 200
    data = boot.get_json()
    assert data['user']
    assert isinstance(data['notes'], list)

    created = client.post('/api/ide/notes', json={'folder': '工作/测试'})
    assert created.status_code == 201
    note_id = created.get_json()['id']

    saved = client.put(f'/api/ide/notes/{note_id}', json={
        'content': '# IDE 测试\n本地优先',
        'tags': ['同步', '本地'],
        'folder': '工作/测试',
    })
    assert saved.status_code == 200

    detail = client.get(f'/api/ide/notes/{note_id}').get_json()
    assert '本地优先' in detail['content']
    assert detail['tags'] == ['同步', '本地']
    assert detail['folder'] == '工作/测试'

    found = client.get('/api/ide/search?q=本地优先').get_json()
    assert any(item['id'] == note_id for item in found['items'])

    assert client.delete(f'/api/ide/notes/{note_id}').status_code == 200
    assert client.get(f'/api/ide/notes/{note_id}').status_code == 404


def test_remote_workspace_api(monkeypatch):
    from cloudsync import service as sync_service
    from cloudsync import settings as sync_settings

    sync_settings.save_settings({
        "remote_url": "https://note.example.com",
        "remote_user": "alice",
        "session_cookie": "cookie-value",
        "local_user": "syncuser",
    })

    class FakeClient:
        def list_remote_notes(self):
            return ["abcd"]

        def read_note(self, note_id):
            return {
                "id": note_id,
                "content": "# 云端标题\n云端正文",
                "tags": "云,同步",
                "folder": "工作/云端",
            }

        def create_note(self, folder=""):
            return "new1"

        def post_note(self, *args, **kwargs):
            return True

        def delete_note(self, note_id):
            return True

    monkeypatch.setattr(sync_service, "make_client", lambda settings: FakeClient())
    client = _client()

    status = client.get('/api/ide/remote/status').get_json()
    assert status['configured'] is True
    assert status['user'] == 'alice'

    rows = client.get('/api/ide/remote/notes').get_json()['notes']
    assert rows[0]['id'] == 'abcd'
    assert rows[0]['title'] == '云端标题'
    assert rows[0]['folder'] == '工作/云端'

    detail = client.get('/api/ide/remote/notes/abcd').get_json()
    assert '云端正文' in detail['content']

    assert client.post('/api/ide/remote/notes', json={'folder': '云端'}).status_code == 201
    assert client.put('/api/ide/remote/notes/abcd', json={
        'content': '新内容', 'tags': ['a'], 'folder': '云端',
    }).status_code == 200
    assert client.delete('/api/ide/remote/notes/abcd').status_code == 200


def test_sync_api_status_and_settings():
    client = _client()
    status = client.get('/api/ide/sync/status').get_json()
    assert 'settings' in status and 'runs' in status

    saved = client.put('/api/ide/sync/settings', json={
        'remote_url': 'note.example.com',
        'remote_user': 'alice',
        'session_cookie': 'cookie-value',
    })
    assert saved.status_code == 200
    status = client.get('/api/ide/sync/status').get_json()
    assert status['settings']['remote_url'] == 'https://note.example.com'
    assert status['settings']['cookie_configured'] is True


def test_note_title_and_save_as():
    client = _client()
    created = client.post('/api/ide/notes', json={'folder': '', 'title': '我的自定义名称'}).get_json()
    note_id = created['id']

    detail = client.get(f'/api/ide/notes/{note_id}').get_json()
    assert detail['title'] == '我的自定义名称'

    rows = client.get('/api/ide/bootstrap').get_json()['notes']
    row = next(r for r in rows if r['id'] == note_id)
    assert row['title'] == '我的自定义名称'

    saved_as = client.post('/api/ide/notes/save-as', json={
        'title': '副本名称', 'content': '# 副本\n内容', 'tags': ['x'], 'folder': '备份',
    })
    assert saved_as.status_code == 201
    copy_id = saved_as.get_json()['id']
    copy = client.get(f'/api/ide/notes/{copy_id}').get_json()
    assert copy['title'] == '副本名称'
    assert '副本' in copy['content']
    assert copy['folder'] == '备份'

    client.delete(f'/api/ide/notes/{note_id}')
    client.delete(f'/api/ide/notes/{copy_id}')


def test_workspace_paths_and_cache(monkeypatch, tmp_path):
    from cloudsync import service as sync_service
    from cloudsync import settings as sync_settings
    from ideapi import workspace

    cache_dir = tmp_path / 'cache'
    local_dir = tmp_path / 'local'
    sync_settings.save_settings({
        "remote_url": "https://note.example.com",
        "remote_user": "alice",
        "session_cookie": "cookie-value",
        "local_user": "syncuser",
        "local_notes_dir": str(local_dir),
        "cloud_cache_dir": str(cache_dir),
    })

    class FakeClient:
        def list_remote_notes(self):
            return ["abcd"]

        def read_note(self, note_id):
            return {"content": "# 缓存正文", "tags": "云", "folder": "工作"}

        def post_note(self, *args, **kwargs):
            return True

    monkeypatch.setattr(sync_service, "make_client", lambda settings: FakeClient())
    client = _client()

    paths = client.get('/api/ide/workspace/paths').get_json()
    assert paths['cloudDir'] == str(cache_dir)
    assert paths['customCloud'] is True

    pulled = client.post('/api/ide/workspace/cloud/pull').get_json()
    assert pulled['ok'] == 1

    files = client.get('/api/ide/workspace/cloud/files').get_json()['files']
    assert len(files) == 1
    assert files[0]['id'] == 'abcd'

    cached = client.get('/api/ide/workspace/cloud/files/abcd').get_json()
    assert '缓存正文' in cached['content']

    saved = client.put('/api/ide/workspace/cloud/files/abcd', json={
        'content': '# 编辑后', 'title': '缓存标题', 'tags': ['a'], 'folder': '工作',
    }).get_json()
    assert saved['ok'] is True
    assert saved['pushed'] is True

    assert client.delete('/api/ide/workspace/cloud/files/abcd').status_code == 200
    assert client.get('/api/ide/workspace/cloud/files/abcd').status_code == 404
