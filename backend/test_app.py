"""API contract tests. SQLite isolates tests; deployment uses MySQL."""
import importlib
import os
import base64

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'test.db'))
    monkeypatch.setenv('OWNER_PASSWORD', 'test-only-password-at-least-20')
    import main
    importlib.reload(main)
    with TestClient(main.app) as client:
        client.headers['Authorization'] = 'Basic ' + base64.b64encode(b'owner:test-only-password-at-least-20').decode()
        yield client
    main.engine.dispose()

def test_task_lifecycle(client):
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

def test_public_cannot_mutate_anything(client):
    id = client.get('/api/state').json()['lists'][0]['id']
    task = client.post('/api/tasks', json={'title': 'Protected', 'list_id': id}).json()
    before = client.get('/api/state').json()
    del client.headers['Authorization']
    assert client.get('/api/state').status_code == 200
    routes = [
        ('POST', '/api/lists', {'name':'Intruder'}),
        ('PUT', f'/api/lists/{id}', {'name':'Changed'}),
        ('DELETE', f'/api/lists/{id}', None),
        ('POST', '/api/tasks', {'title':'Intruder', 'list_id':id}),
        ('PUT', f"/api/tasks/{task['id']}", {'title':'Changed', 'list_id':id}),
        ('DELETE', f"/api/tasks/{task['id']}", None),
        ('PUT', f'/api/lists/{id}/order', {'ids':[task['id']]}),
    ]
    for method, path, data in routes:
        assert client.request(method, path, json=data).status_code == 401
    assert client.get('/api/state').json() == before

def test_owner_auth_and_fail_closed(client, monkeypatch):
    assert client.get('/api/owner').status_code == 200
    client.headers['Authorization'] = 'Basic ' + base64.b64encode(b'owner:wrong').decode()
    assert client.get('/api/owner').status_code == 401
    monkeypatch.delenv('OWNER_PASSWORD')
    assert client.post('/api/lists', json={'name':'Blocked'}).status_code == 503
    assert client.get('/api/state').status_code == 200

def test_password_guessing_is_limited(client):
    client.headers['Authorization'] = 'Basic ' + base64.b64encode(b'owner:wrong').decode()
    for _ in range(10):
        assert client.get('/api/owner').status_code == 401
    assert client.get('/api/owner').status_code == 429
