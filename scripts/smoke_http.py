"""Launch a real loopback API, serve the built web app, run Bandit, then tear down."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]

def main():
    if not (ROOT / 'web/dist/index.html').is_file():
        raise SystemExit('Build the web client first: cd web && npm ci && npm run build')
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='grim-http-') as data:
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', str(port)], cwd=ROOT,
                                env={**os.environ, 'GRIM_DATA_DIR': data}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=10, trust_env=False) as c:
                for _ in range(60):
                    try:
                        if c.get('/health').status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    time.sleep(.1)
                assert c.get('/health').json()['status'] == 'ok'
                page = c.get('/')
                assert page.status_code == 200 and 'root' in page.text
                result = c.post('/api/auth/register', json={'email': 'smoke@example.test', 'password': 'temporary-smoke-password'} )
                assert result.status_code == 200, result.text
                c.headers['Authorization'] = 'Bearer ' + result.json()['token']
                result = c.post('/api/tasks', json={'command': 'Inspect a sample with real Bandit', 'steps': [
                    {'tool': 'write_file', 'args': {'path': 'sample.py', 'content': 'import subprocess\nsubprocess.run("echo test", shell=True)\n'}},
                    {'tool': 'bandit', 'args': {}}]})
                assert result.status_code == 200, result.text
                task_id = result.json()['id']
                for _ in range(100):
                    task = c.get('/api/tasks/' + task_id).json()
                    if task['status'] not in ('queued', 'running'):
                        break
                    time.sleep(.1)
                assert task['status'] == 'completed', task
                findings = task['result']['events'][-1]['output']['findings']
                assert any(item['rule'] == 'B602' for item in findings), findings
                assert c.post('/api/emergency-stop').json()['stopped']
                assert c.post('/api/tasks', json={'command': 'list', 'steps': [{'tool': 'list_files'}]}).status_code == 423
                assert c.post('/api/auth/logout').status_code == 200
                assert c.get('/api/memory').status_code == 401
                print('PASS: real HTTP server, built web HTML, authentication, real Bandit task, emergency stop, logout')
        finally:
            proc.terminate()
            proc.wait(timeout=10)

if __name__ == '__main__':
    main()
