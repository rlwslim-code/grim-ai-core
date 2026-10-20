"""Read-only Shadow research diagnostics and bounded static artifact triage."""
import asyncio
import base64
import binascii
import hashlib
import os
import shutil
import socket
from pathlib import Path

MAX_ARTIFACT = 2 * 1024 * 1024
TOOLS = {'nmap':'nmap', 'semgrep':'semgrep', 'owasp-zap':'zaproxy', 'metasploit':'msfconsole',
         'ghidra':'ghidraRun', 'wireshark':'tshark', 'mobsf':'mobsf', 'afl++':'afl-fuzz',
         'yara':'yara', 'radare2':'r2', 'volatility':'vol'}

def arsenal():
    return [{'name': name, 'installed': bool(shutil.which(binary)), 'invokable': False,
             'path': shutil.which(binary), 'status': 'detected-unverified' if shutil.which(binary) else 'absent',
             'reason': 'No authorized execution adapter configured'} for name,binary in TOOLS.items()]

async def tor_gateway():
    """SOCKS5 handshake checks *local* Tor proxy; no remote sites are contacted."""
    host = os.getenv('GRIM_TOR_PROXY_HOST', '127.0.0.1')
    port_text = os.getenv('GRIM_TOR_PROXY_PORT', '9050')
    # Never let remote clients use this diagnostic to scan arbitrary destinations.
    if host not in ('127.0.0.1', '::1', 'localhost'):
        return {'state': 'disabled', 'reason': 'Only loopback proxy diagnostics are supported'}
    try:
        port = int(port_text)
        if not (1 <= port <= 65535): raise ValueError()
    except ValueError:
        return {'state': 'misconfigured', 'reason': 'Invalid local proxy port'}
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=1.5)
        try:
            writer.write(b'\x05\x01\x00')
            await asyncio.wait_for(writer.drain(), timeout=1.5)
            response = await asyncio.wait_for(reader.readexactly(2), timeout=1.5)
            return {'state': 'proxy-detected' if response == b'\x05\x00' else 'unavailable',
                    'reason': 'SOCKS5 handshake accepted; Tor routing is NOT verified' if response == b'\x05\x00' else 'SOCKS5 handshake rejected'}
        finally:
            writer.close()
            await writer.wait_closed()
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError):
        return {'state': 'unavailable', 'reason': 'No responding local SOCKS5 proxy'}

def inspect_artifact(encoded: str):
    if len(encoded) > (MAX_ARTIFACT * 4 // 3 + 8):
        raise ValueError('Artifact exceeds 2 MiB limit')
    try: content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError): raise ValueError('Invalid base64 artifact')
    if len(content) > MAX_ARTIFACT: raise ValueError('Artifact exceeds 2 MiB limit')
    kinds = [(b'MZ','PE executable'),(b'\x7fELF','ELF binary'),(b'PK\x03\x04','ZIP/APK archive'),(b'\xca\xfe\xba\xbe','Java class / Mach-O fat'),(b'\x00asm','WebAssembly')]
    kind = next((label for magic,label in kinds if content.startswith(magic)), 'Unknown / raw data')
    indicators = []
    for signature, label in ((b'http://','HTTP URL literal'),(b'https://','HTTPS URL literal'),(b'powershell','PowerShell literal'),(b'cmd.exe','Windows shell literal')):
        if signature in content.lower(): indicators.append(label)
    return {'sha256':hashlib.sha256(content).hexdigest(),'sha1':hashlib.sha1(content).hexdigest(),
            'size_bytes':len(content),'file_type':kind,'heuristic_indicators':indicators,
            'verdict':'not-determined','executed':False}
