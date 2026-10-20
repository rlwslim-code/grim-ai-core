"""Docker laboratory lifecycle. Containers are not virtual machines."""
from __future__ import annotations
import asyncio
import hashlib
import json
import importlib.util
import shutil

TOOL_BINARIES = {'nmap': 'nmap', 'wireshark': 'tshark', 'zap': 'zaproxy', 'burp-community': 'burpsuite',
                 'metasploit': 'msfconsole', 'ghidra': 'ghidraRun', 'mobsf': 'mobsf', 'semgrep': 'semgrep', 'afl++': 'afl-fuzz'}


def discover_tools() -> list[dict]:
    return [{'name': 'bandit', 'installed': importlib.util.find_spec('bandit') is not None, 'invokable': importlib.util.find_spec('bandit') is not None, 'capabilities': ['static-python-analysis'], 'environment': 'backend'}, {'name': 'grim-ast', 'installed': True, 'invokable': True, 'capabilities': ['static-python-analysis'], 'environment': 'backend'}] + [
        {'name': name, 'installed': bool(shutil.which(binary)), 'invokable': False,
         'capabilities': [], 'environment': 'backend', 'reason': 'Discovery only; scoped invocation adapter requires separate configuration'}
        for name, binary in TOOL_BINARIES.items()]


class LabManager:
    def __init__(self, namespace: str = 'default', image: str = 'grim-sandbox:1'):
        self.name = 'grim-lab-' + hashlib.sha256(namespace.encode()).hexdigest()[:20]
        self.image = image
        self.lock = asyncio.Lock()

    async def _docker(self, *args):
        if not shutil.which('docker'):
            return 127, 'Docker unavailable'
        try:
            p = await asyncio.create_subprocess_exec('docker', *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            out, _ = await asyncio.wait_for(p.communicate(), 10)
            return p.returncode, out[:65536].decode(errors='replace')
        except asyncio.TimeoutError:
            p.kill()
            await p.wait()
            return 124, 'Docker operation timeout'
        except OSError as exc:
            return 127, str(exc)

    async def status(self):
        code, out = await self._docker('info', '--format', '{{.ServerVersion}}')
        if code:
            return {'state': 'unavailable', 'kind': 'container', 'reason': out, 'vm': {'state': 'awaiting_infrastructure', 'kind': 'kali-virtual-machine'}}
        code, out = await self._docker('inspect', '--format', '{{json .State}}', self.name)
        if code:
            return {'state': 'stopped', 'kind': 'container', 'vm': {'state': 'awaiting_infrastructure'}}
        state = json.loads(out)
        return {'state': 'running' if state.get('Running') else 'stopped', 'kind': 'container', 'image': self.image,
                'network': 'none', 'vm': {'state': 'awaiting_infrastructure'}}

    async def create(self):
        async with self.lock:
            status = await self.status()
            if status['state'] in ('running', 'unavailable'):
                return status
            await self._docker('rm', '-f', self.name)
            code, out = await self._docker('run', '-d', '--pull=never', '--name', self.name, '--network', 'none',
                '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '32',
                '--memory', '128m', '--memory-swap', '128m', '--cpus', '0.25', '--user', '65534:65534',
                '--tmpfs', '/tmp:rw,noexec,nosuid,size=16m', self.image, 'python', '-c', 'import time; time.sleep(86400)')
            return {'state': 'unavailable', 'kind': 'container', 'reason': out} if code else await self.status()

    async def stop(self):
        async with self.lock:
            code, out = await self._docker('rm', '-f', self.name)
            if code and 'No such container' not in out:
                return {'state': 'unavailable', 'kind': 'container', 'reason': out}
            return {'state': 'stopped', 'kind': 'container'}

    async def reset(self):
        result = await self.stop()
        if result['state'] == 'unavailable':
            return result
        return await self.create()


class KaliVMAdapter:
    """Explicit unconfigured integration boundary; never treats Docker as a VM."""
    def status(self):
        return {'state': 'awaiting_infrastructure', 'kind': 'virtual-machine',
                'requirements': ['Hardware virtualization', 'Configured hypervisor adapter', 'Kali image and isolated network']}

    def create(self):
        raise RuntimeError('Kali VM hypervisor is not configured')
