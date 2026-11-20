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
