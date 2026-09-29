"""API contract tests. SQLite isolates tests; deployment uses MySQL."""
import importlib

import pytest
from fastapi.testclient import TestClient

@pytest.fixture(params=[None, 'legacy-owner-password-at-least-20'])
def client(tmp_path, monkeypatch, request):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'test.db'))
    if request.param is None:
        monkeypatch.delenv('OWNER_PASSWORD', raising=False)
    else:
        monkeypatch.setenv('OWNER_PASSWORD', request.param)
    import main
    importlib.reload(main)
    with TestClient(main.app) as client:
        yield client
    main.engine.dispose()

def test_task_lifecycle_without_login(client):
    assert 'Authorization' not in client.headers
    first = client.get('/api/state').json()['lists'][0]['id']
    second = client.post('/api/lists', json={'name': 'Work'}).json()['id']
    a = client.post('/api/tasks', json={'title': 'First', 'list_id': first}).json()
    b = client.post('/api/tasks', json={'title': 'Second', 'list_id': first}).json()
    assert client.put(f'/api/lists/{first}/order', json={'ids': [b['id'], a['id']]}).status_code == 200
    assert [t['id'] for t in client.get('/api/state').json()['tasks']] == [b['id'], a['id']]
    a.update(title='Edited', note='A saved note', completed=True, list_id=second)
    saved = client.put(f"/api/tasks/{a['id']}", json=a).json()
    assert saved['completed'] and saved['note'] == 'A saved note' and saved['list_id'] == second
    assert client.put(f'/api/lists/{second}', json={'name':'Renamed'}).status_code == 200
    assert client.delete(f'/api/lists/{second}').status_code == 200
    assert [t['id'] for t in client.get('/api/state').json()['tasks']] == [b['id']]
    assert client.delete(f"/api/tasks/{b['id']}").status_code == 200
    assert client.get('/api/state').json()['tasks'] == []

def test_invalid_input_and_order(client):
    id = client.get('/api/state').json()['lists'][0]['id']
    assert client.post('/api/tasks', json={'title':'   ', 'list_id':id}).status_code == 422
    assert client.post('/api/lists', json={'name':' '}).status_code == 422
    assert client.post('/api/tasks', json={'title':'Task', 'list_id':999}).status_code == 404
    task = client.post('/api/tasks', json={'title':'Task', 'list_id':id}).json()
    for ids in ([], [task['id'],task['id']], [999]):
        assert client.put(f'/api/lists/{id}/order', json={'ids':ids}).status_code == 409
    assert len(client.get('/api/state').json()['tasks']) == 1

