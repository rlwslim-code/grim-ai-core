import base64
import hashlib
import pytest
from backend import shadow
from fastapi.testclient import TestClient
from backend.main import app

def test_static_inspection_never_executes():
    binary=b'MZ\x00https://example.test/payload'
    result=shadow.inspect_artifact(base64.b64encode(binary).decode())
    assert result['sha256']==hashlib.sha256(binary).hexdigest()
    assert result['file_type']=='PE executable'
    assert not result['executed']
    assert result['verdict']=='not-determined'

def test_invalid_and_oversized():
    with pytest.raises(ValueError): shadow.inspect_artifact('not*base64')
    with pytest.raises(ValueError): shadow.inspect_artifact(base64.b64encode(b'A'*(shadow.MAX_ARTIFACT+1)).decode())

def test_arsenal_does_not_claim_execution():
    assert all(t['invokable'] is False for t in shadow.arsenal())

@pytest.mark.asyncio
async def test_tor_non_loopback_refused(monkeypatch):
    monkeypatch.setenv('GRIM_TOR_PROXY_HOST','8.8.8.8')
    assert (await shadow.tor_gateway())['state']=='disabled'

@pytest.mark.asyncio
async def test_tor_unavailable(monkeypatch):
    monkeypatch.setenv('GRIM_TOR_PROXY_HOST','127.0.0.1')
    monkeypatch.setenv('GRIM_TOR_PROXY_PORT','0')
    assert (await shadow.tor_gateway())['state']=='misconfigured'

def test_requires_auth():
    c=TestClient(app)
    assert c.get('/api/shadow/status').status_code==401
    assert c.post('/api/shadow/inspect',json={'data_base64':'QQ=='}).status_code==401
