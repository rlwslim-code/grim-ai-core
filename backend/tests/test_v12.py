import json
import pytest
from unittest.mock import patch
from backend.providers import ModelProvider, ProviderUnavailable, classify_error
import httpx

@pytest.mark.asyncio
async def test_provider_stream_real_sse_protocol():
    def handle(request):
        assert request.url.path.endswith('/chat/completions')
        assert json.loads(request.content)['stream'] is True
        return httpx.Response(200,text='data: {"choices":[{"delta":{"content":"Rav"}}]}\n\ndata: {"choices":[{"delta":{"content":"’kael"}}]}\n\ndata: [DONE]\n\n',headers={'Content-Type':'text/event-stream'})
    class Client(httpx.AsyncClient):
        def __init__(self,*args,**kwargs):
            kwargs['transport']=httpx.MockTransport(handle)
            super().__init__(*args,**kwargs)
    with patch('backend.providers.httpx.AsyncClient',Client):
        p=ModelProvider()
        assert ''.join([chunk async for chunk in p.stream([{'role':'user','content':'hi'}])])=='Rav’kael'

@pytest.mark.asyncio
async def test_provider_auth_failure_category():
    def handle(request): return httpx.Response(401)
    class Client(httpx.AsyncClient):
        def __init__(self,*args,**kwargs):
            kwargs['transport']=httpx.MockTransport(handle)
            super().__init__(*args,**kwargs)
    with patch('backend.providers.httpx.AsyncClient',Client):
        with pytest.raises(ProviderUnavailable) as exc:
            await ModelProvider().complete([{'role':'user','content':'hello'}])
        assert exc.value.category=='authentication_failure'

@pytest.mark.asyncio
async def test_provider_fallback(monkeypatch):
    monkeypatch.setenv('GRIM_MODEL_FALLBACKS',json.dumps([{'base_url':'http://fallback.local/v1','model':'model2'}]))
    def handle(request):
        if request.url.host=='127.0.0.1': return httpx.Response(503)
        return httpx.Response(200,json={'choices':[{'message':{'content':'working'}}]})
    class Client(httpx.AsyncClient):
        def __init__(self,*args,**kwargs):
            kwargs['transport']=httpx.MockTransport(handle)
            super().__init__(*args,**kwargs)
    with patch('backend.providers.httpx.AsyncClient',Client):
        assert await ModelProvider().complete([{'role':'user','content':'hello'}])=='working'
