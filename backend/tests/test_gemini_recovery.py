import pytest
import httpx
from backend.providers import ModelProvider

@pytest.mark.asyncio
async def test_gemini_recovery_from_account_model_list(monkeypatch):
    monkeypatch.setenv('GRIM_MODEL_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta/openai')
    monkeypatch.setenv('GRIM_MODEL_API_KEY', 'test-key')
    monkeypatch.setenv('GRIM_MODEL', 'invalid-model')
    provider = ModelProvider()
    actual_client = httpx.AsyncClient
    def client_factory(*args, **kwargs):
        def respond(request):
            assert request.url.path == '/v1beta/models'
            return httpx.Response(200, json={'models': [
                {'name':'models/gemini-2.5-flash', 'supportedGenerationMethods':['generateContent']},
                {'name':'models/text-embedding-004', 'supportedGenerationMethods':['embedContent']},
            ]})
        kwargs['transport'] = httpx.MockTransport(respond)
        return actual_client(*args, **kwargs)
    monkeypatch.setattr('backend.providers.httpx.AsyncClient', client_factory)
    selected = await provider._gemini_recovery_model(provider._endpoints()[0])
    assert selected == 'gemini-2.5-flash'

@pytest.mark.asyncio
async def test_gemini_recovery_does_not_probe_without_key(monkeypatch):
    monkeypatch.setenv('GRIM_MODEL_API_KEY', '')
    provider = ModelProvider()
    assert await provider._gemini_recovery_model({'base':'https://generativelanguage.googleapis.com/v1beta/openai','key':'','model':'bad'}) is None
