import pytest
import httpx
from backend.providers import ModelProvider

@pytest.mark.asyncio
async def test_readiness_reports_connection_failure(monkeypatch):
    monkeypatch.setenv('GRIM_MODEL_BASE_URL','http://127.0.0.1:1/v1')
    model=ModelProvider()
    result=await model.readiness()
    assert result['reachable'] is False
    assert result['model_available'] is False
    assert 'key' not in str(result).lower()

@pytest.mark.asyncio
async def test_readiness_reports_model_availability(monkeypatch):
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,*args,**kwargs):
            return httpx.Response(200,json={'data':[{'id':'qwen2.5:3b'}]},request=httpx.Request('GET','http://localhost/v1/models'))
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    monkeypatch.setenv('GRIM_MODEL','qwen2.5:3b')
    model=ModelProvider()
    result=await model.readiness()
    assert result['reachable'] is True
    assert result['model_available'] is True
    assert isinstance(result['latency_ms'],int)
