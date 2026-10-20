import asyncio
from pathlib import Path
from unittest.mock import patch
from backend.executor import Executor, analyze_python
from backend.labs import LabManager, discover_tools


def run(coro):
    return asyncio.run(coro)


def test_files_and_path_boundary(tmp_path):
    e = Executor(tmp_path)
    assert run(e.execute('write_file', {'path': 'src/app.py', 'content': 'print(2)'}))['ok']
    assert run(e.execute('read_file', {'path': 'src/app.py'}))['content'] == 'print(2)'
    for path in ('../escape', '/etc/passwd', '.secrets'):
        assert not run(e.execute('read_file', {'path': path}))['ok']
    (tmp_path / 'link').symlink_to('/tmp')
    assert not run(e.execute('write_file', {'path': 'link/escape', 'content': 'x'}))['ok']


def test_security_analysis():
    result = analyze_python('import subprocess\nsubprocess.run("hi", shell=True)\npassword="hidden"')
    assert {x['rule'] for x in result['findings']} == {'process-execution', 'shell-true', 'hardcoded-secret'}
    assert 'hidden' not in str(result)
    assert not analyze_python('if :')['valid_python']


def test_fail_closed_and_emergency(tmp_path):
    e = Executor(tmp_path)
    run(e.execute('write_file', {'path': 'a.py', 'content': 'print(1)'}))
    with patch('backend.executor.shutil.which', return_value=None):
        assert run(e.execute('python', {'path': 'a.py'}))['unavailable']
    run(e.stop())
    assert not run(e.execute('write_file', {'path': 'b.py', 'content': 'x'}))['ok']
    e.resume()
    assert run(e.execute('list_files', {}))['ok']
    assert not run(e.execute('shell', {'command': 'id'}))['ok']


def test_labs_fail_closed():
    with patch('backend.labs.shutil.which', return_value=None):
        assert run(LabManager().create())['state'] == 'unavailable'
        assert any(t['name'] == 'grim-ast' and t['invokable'] for t in discover_tools())


def test_real_bandit(tmp_path):
    import importlib.util
    import pytest
    if importlib.util.find_spec('bandit') is None:
        pytest.skip('Bandit dependency unavailable')
    e = Executor(tmp_path)
    run(e.execute('write_file', {'path': 'sample.py', 'content': 'import subprocess\nsubprocess.run("hello",shell=True)\npassword="private_literal"\n'}))
    result = run(e.execute('bandit', {}))
    assert result['ok'], result
    assert any(f['rule'] == 'B602' for f in result['findings'])
    assert 'private_literal' not in str(result)
