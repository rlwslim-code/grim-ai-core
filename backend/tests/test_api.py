import os, tempfile
os.environ.setdefault('GRIM_DATA_DIR', tempfile.mkdtemp(prefix='grim-tests-'))
os.environ['GRIM_ALLOW_REGISTRATION']='1'
from fastapi.testclient import TestClient
from backend.main import app
from backend import core,db
from backend.providers import ProviderUnavailable
import uuid

client=TestClient(app)
def account():
    r=client.post('/api/auth/register',json={'email':uuid.uuid4().hex+'@example.test','password':'a-long-test-password'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def test_auth_and_memory_isolation():
    a,b=account(),account()
    assert client.get('/api/memory').status_code==401
    r=client.post('/api/memory',headers=a,json={'content':'Remember Obsidian','kind':'preference'})
    assert r.status_code==200
    mid=r.json()['id']
    assert len(client.get('/api/memory',headers=a).json())==1
    assert client.get('/api/memory',headers=b).json()==[]
    client.delete('/api/memory/'+mid,headers=b)
    assert len(client.get('/api/memory',headers=a).json())==1
    client.put('/api/memory/'+mid,headers=a,json={'content':'Remember Abyss'})
    assert client.get('/api/memory',headers=a).json()[0]['content']=='Remember Abyss'
    raw=db.query('SELECT content FROM memory WHERE id=?',(mid,))[0]['content']
    assert 'Abyss' not in raw
    client.delete('/api/memory/'+mid,headers=a)
    assert client.get('/api/memory',headers=a).json()==[]

def test_chat_persistence_and_unavailable(monkeypatch):
    a=account()
    async def complete(messages,json_mode=False): return 'Rav’kael. Test response.'
    monkeypatch.setattr(core.provider,'complete',complete)
    r=client.post('/api/chat',headers=a,json={'message':'Hello','mode':'ABYSS'})
    assert r.status_code==200,r.text
    cid=r.json()['conversation_id']
    assert len(client.get('/api/conversations/'+cid,headers=a).json())==2
    assert client.get('/api/conversations/'+cid,headers=account()).status_code==404
    async def unavailable(*args,**kwargs): raise ProviderUnavailable('Model unavailable')
    monkeypatch.setattr(core.provider,'complete',unavailable)
    assert client.post('/api/chat',headers=a,json={'message':'Next'}).status_code==503

def test_stop_revoke_and_tool_plan():
    a=account()
    assert client.post('/api/tasks',headers=a,json={'command':'invalid','steps':[{'tool':'shell','args':{'command':'id'}}]}).status_code==422
    assert client.post('/api/emergency-stop',headers=a).json()['stopped']
    assert client.post('/api/tasks',headers=a,json={'command':'list','steps':[{'tool':'list_files'}]}).status_code==423
    assert client.post('/api/labs',headers=a,json={'action':'create'}).status_code==423
    assert client.post('/api/resume',headers=a).json()['stopped'] is False
    assert client.post('/api/auth/revoke-all',headers=a).status_code==200
    assert client.get('/api/memory',headers=a).status_code==401
