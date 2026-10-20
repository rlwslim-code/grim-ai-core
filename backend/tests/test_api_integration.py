"""Real API/storage/executor integration; never substitutes fake model output."""
import subprocess
import sys
import time
import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend import db


def test_real_auth_memory_tasks_stop_and_revocation(monkeypatch):
    monkeypatch.setenv('GRIM_ALLOW_REGISTRATION', '1')
    email = 'integration-' + uuid.uuid4().hex + '@example.test'
    with TestClient(app) as client:
        response = client.post('/api/auth/register', json={'email': email, 'password': 'Integration-passphrase-123'})
        assert response.status_code == 200, response.text
        token = response.json()['token']
        headers = {'Authorization': 'Bearer ' + token}
        assert client.get('/api/memory').status_code == 401
        memory_text = 'integration-private-' + uuid.uuid4().hex
        saved = client.post('/api/memory', headers=headers, json={'content': memory_text, 'kind': 'preference'})
        assert saved.status_code == 200
        memory_id = saved.json()['id']
        row = db.query('SELECT content FROM memory WHERE id=?', (memory_id,))[0]
        assert memory_text not in row['content']
        # A separate Python process must reopen the on-disk DB and encryption key.
        reopened = subprocess.run([sys.executable, '-c', 'from backend import db; import sys; r=db.query("SELECT content FROM memory WHERE id=?",(sys.argv[1],))[0]; print(db.unseal(r["content"]))', memory_id], check=True, capture_output=True, text=True)
        assert reopened.stdout.strip() == memory_text
        assert client.get('/api/memory', headers=headers).json()[0]['content'] == memory_text
        assert client.put('/api/memory/' + memory_id, headers=headers, json={'content': 'changed preference'}).status_code == 200
        task = client.post('/api/tasks', headers=headers, json={'command': 'Write and analyze harmless sample', 'steps': [
            {'tool': 'write_file', 'args': {'path': 'sample.py', 'content': 'x = eval("2 + 2")\n'}},
            {'tool': 'analyze_python', 'args': {'path': 'sample.py'}}
        ]})
        assert task.status_code == 200, task.text
        task_id = task.json()['id']
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            record = client.get('/api/tasks/' + task_id, headers=headers).json()
            if record['status'] not in ('queued', 'running'):
                break
            time.sleep(.02)
        assert record['status'] == 'completed', record
        output = record['result']['events'][-1]['output']
        assert output['tool'] == 'grim-ast'
        assert any(f['rule'] == 'dynamic-evaluation' for f in output['findings'])
        assert client.post('/api/emergency-stop', headers=headers).json()['stopped'] is True
        rejected = client.post('/api/tasks', headers=headers, json={'command': 'list', 'steps': [{'tool': 'list_files', 'args': {}}]})
        assert rejected.status_code == 423
        assert client.post('/api/resume', headers=headers).status_code == 200
        assert client.delete('/api/memory/' + memory_id, headers=headers).status_code == 200
        assert client.post('/api/auth/logout', headers=headers).status_code == 200
        assert client.get('/api/memory', headers=headers).status_code == 401
        login = client.post('/api/auth/login', json={'email': email, 'password': 'Integration-passphrase-123'})
        assert login.status_code == 200
        assert login.json()['token'] != token
