"""Structured tools. Untrusted programs run ONLY inside hardened Docker containers."""
from __future__ import annotations
import ast
import asyncio
import hashlib
import json
import importlib.util
import sys
import os
from pathlib import Path
import shutil
import uuid

MAX_FILE = 262_144
MAX_WORKSPACE = 10_485_760
TOOLS = {
    'bandit': {'description': 'Run Bandit Python static security analysis; no source execution', 'arguments': {}},
    'write_file': {'description': 'Write UTF-8 project file', 'arguments': {'path': 'relative path', 'content': 'text'}},
    'read_file': {'description': 'Read project file', 'arguments': {'path': 'relative path'}},
    'list_files': {'description': 'List project files', 'arguments': {}},
    'python': {'description': 'Run a Python project file in a networkless container', 'arguments': {'path': 'relative .py file'}},
    'pytest': {'description': 'Run project tests in a networkless container', 'arguments': {}},
    'analyze_python': {'description': 'Static AST security analysis, without executing source', 'arguments': {'path': 'relative .py file'}},
}


def analyze_python(source: str) -> dict:
    """Small real static analyzer; results are indicators requiring human review."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {'tool': 'grim-ast', 'valid_python': False, 'findings': [{'line': exc.lineno, 'rule': 'syntax-error', 'detail': exc.msg}]}
    findings = []
    risky = {'eval': 'dynamic-evaluation', 'exec': 'dynamic-evaluation', 'pickle.loads': 'unsafe-deserialization',
             'pickle.load': 'unsafe-deserialization', 'os.system': 'shell-command', 'subprocess.Popen': 'process-execution',
             'subprocess.run': 'process-execution', 'yaml.load': 'unsafe-deserialization', 'marshal.loads': 'unsafe-deserialization'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if name in risky:
                findings.append({'line': node.lineno, 'rule': risky[name], 'detail': name})
            for kw in node.keywords:
                if kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    findings.append({'line': node.lineno, 'rule': 'shell-true', 'detail': 'Process uses shell=True'})
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and any(word in target.id.lower() for word in ('password', 'secret', 'api_key', 'token')) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
                    findings.append({'line': node.lineno, 'rule': 'hardcoded-secret', 'detail': 'Possible credential literal; value redacted'})
    return {'tool': 'grim-ast', 'valid_python': True, 'findings': findings, 'limitations': 'Syntax-based indicators only; not a complete vulnerability assessment.'}


class Executor:
    def __init__(self, root: str | Path, image: str = 'grim-sandbox:1', timeout: int = 20):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.image = image
        self.timeout = min(max(timeout, 1), 60)
        self.active: dict[str, str] = {}
        self.parsers: dict[str, asyncio.subprocess.Process] = {}
        self.halted = False
        self._lock = asyncio.Lock()

    def _path(self, value: str) -> Path:
        if not isinstance(value, str) or not value or len(value) > 240:
            raise ValueError('A relative project path is required')
        p = Path(value)
        if p.is_absolute() or '..' in p.parts or any(x.startswith('.') for x in p.parts):
            raise ValueError('Path outside workspace or hidden path denied')
        target = self.root / p
        if any(part.is_symlink() for part in [target, *target.parents] if part != self.root.parent):
            raise ValueError('Symbolic links are denied')
        if not target.resolve().is_relative_to(self.root):
            raise ValueError('Path outside workspace denied')
        return target

    async def execute(self, tool: str, args: dict, task_id: str = '') -> dict:
        if self.halted:
            return {'ok': False, 'error': 'Emergency stop active'}
        if tool not in TOOLS:
            return {'ok': False, 'error': 'Tool not permitted'}
        try:
            async with self._lock:
                if self.halted:
                    return {'ok': False, 'error': 'Emergency stop active'}
                if tool == 'list_files':
                    return {'ok': True, 'files': [str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()][:500]}
                if tool == 'write_file':
                    p = self._path(args.get('path'))
                    content = args.get('content')
                    if not isinstance(content, str) or len(content.encode()) > MAX_FILE:
                        raise ValueError('File must be text, at most 256 KiB')
                    files = [item for item in self.root.rglob('*') if item.is_file() and not item.is_symlink()]
                    if len(files) >= 500 and not p.exists():
                        raise ValueError('Workspace file count limit exceeded')
                    total = sum(item.stat().st_size for item in files) - (p.stat().st_size if p.is_file() else 0)
                    if total + len(content.encode()) > MAX_WORKSPACE:
                        raise ValueError('Workspace quota exceeded')
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(content, encoding='utf-8')
                    return {'ok': True, 'path': str(p.relative_to(self.root)), 'bytes': len(content.encode())}
                if tool in ('read_file', 'analyze_python'):
                    p = self._path(args.get('path'))
                    if p.stat().st_size > MAX_FILE:
                        raise ValueError('File exceeds read limit')
                    source = p.read_text(encoding='utf-8')
                    return {'ok': True, **({'content': source} if tool == 'read_file' else analyze_python(source))}
                if tool == 'bandit':
                    return await self._bandit(task_id or uuid.uuid4().hex)
                if tool == 'python':
                    p = self._path(args.get('path'))
                    if p.suffix != '.py' or not p.is_file():
                        raise ValueError('Existing .py project file required')
                    command = ['python', '-I', str(Path('/workspace') / p.relative_to(self.root))]
                else:
                    command = ['python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '/workspace']
                return await self._container(command, task_id or uuid.uuid4().hex)
        except (ValueError, OSError, UnicodeError) as exc:
            return {'ok': False, 'error': str(exc)}

    async def _bandit(self, task_id: str) -> dict:
        if importlib.util.find_spec('bandit') is None:
            return {'ok': False, 'unavailable': True, 'error': 'Bandit is not installed'}
        # Reject links before handing a recursive tree to an external parser.
        if any(p.is_symlink() for p in self.root.rglob('*')):
            return {'ok': False, 'error': 'Symbolic links in workspace are denied'}
        proc = await asyncio.create_subprocess_exec(sys.executable, '-m', 'bandit', '-q', '-f', 'json', '-r', str(self.root),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        self.parsers[task_id] = proc
        try:
            if self.halted:
                return {'ok': False, 'error': 'Emergency stop active'}
            async def collect():
                data = bytearray()
                while True:
                    chunk = await proc.stdout.read(4096)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > 1_048_576:
                        raise ValueError('Bandit output limit exceeded')
                await proc.wait()
                return data
            raw = await asyncio.wait_for(collect(), self.timeout)
            if proc.returncode not in (0, 1):
                return {'ok': False, 'error': 'Bandit analysis failed'}
            report = json.loads(raw)
            findings = []
            for item in report.get('results', [])[:500]:
                filename = Path(item.get('filename', '')).resolve()
                if not filename.is_relative_to(self.root):
                    continue
                findings.append({'path': str(filename.relative_to(self.root)), 'line': item.get('line_number'),
                    'rule': item.get('test_id'), 'name': item.get('test_name'),
                    'severity': item.get('issue_severity'), 'confidence': item.get('issue_confidence')})
            return {'ok': True, 'tool': 'bandit', 'findings': findings, 'files_analyzed': len(report.get('metrics', {})) - 1,
                    'limitations': 'Static analysis; findings require review. Source snippets and literal values are omitted.'}
        except (asyncio.TimeoutError, ValueError) as exc:
            return {'ok': False, 'error': 'Bandit timeout or output limit' if isinstance(exc, asyncio.TimeoutError) else str(exc)}
        finally:
            self.parsers.pop(task_id, None)
            if proc.returncode is None:
                proc.kill()
                await proc.wait()

    async def _container(self, command: list[str], task_id: str) -> dict:
        if not shutil.which('docker'):
            return {'ok': False, 'unavailable': True, 'error': 'Docker unavailable; host execution is disabled'}
        name = 'grim-run-' + uuid.uuid4().hex
        # Source is mounted read-only; generated outputs use a bounded ephemeral tmpfs.
        argv = ['docker', 'run', '--rm', '--pull=never', '--name', name, '--network', 'none',
                '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--pids-limit', '64', '--memory', '256m', '--memory-swap', '256m', '--cpus', '0.5',
                '--ulimit', 'nofile=128:128', '--user', '65534:65534',
                '--tmpfs', '/tmp:rw,noexec,nosuid,size=32m', '--workdir', '/tmp',
                '--mount', f'type=bind,src={self.root},dst=/workspace,readonly', self.image, *command]
        self.active[task_id] = name
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            if self.halted:
                return {'ok': False, 'error': 'Emergency stop active'}
            async def collect():
                chunks, size = [], 0
                while True:
                    data = await proc.stdout.read(4096)
                    if not data:
                        break
                    size += len(data)
                    if size > 65_536:
                        raise ValueError('Output limit exceeded')
                    chunks.append(data)
                await proc.wait()
                return b''.join(chunks).decode(errors='replace')
            output = await asyncio.wait_for(collect(), self.timeout)
            return {'ok': proc.returncode == 0, 'exit_code': proc.returncode, 'output': output, 'isolation': 'docker-container'}
        except asyncio.TimeoutError:
            return {'ok': False, 'error': 'Execution timeout'}
        except ValueError as exc:
            return {'ok': False, 'error': str(exc)}
        finally:
            await self._remove(name)
            self.active.pop(task_id, None)
            if proc and proc.returncode is None:
                proc.kill()
                await proc.wait()

    async def _remove(self, name: str):
        if shutil.which('docker'):
            try:
                p = await asyncio.create_subprocess_exec('docker', 'rm', '-f', name, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await asyncio.wait_for(p.wait(), 5)
            except asyncio.TimeoutError:
                p.kill()
                await p.wait()
            except OSError:
                pass

    async def stop(self, task_id: str | None = None):
        if task_id is None:
            self.halted = True
        for key, proc in list(self.parsers.items()):
            if task_id is None or key == task_id:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
        for key, name in list(self.active.items()):
            if task_id is None or key == task_id:
                await self._remove(name)
        return {'ok': True, 'halted': self.halted}

    def resume(self):
        self.halted = False
        return {'ok': True, 'halted': False}
