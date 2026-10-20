import asyncio
import os, tempfile
os.environ.setdefault('GRIM_DATA_DIR', tempfile.mkdtemp(prefix='grim-schedules-'))
import time
import uuid
from backend import scheduler,core,db
from backend.main import app
from fastapi.testclient import TestClient


def owner(): return uuid.uuid4().hex
STEPS=[{'tool':'list_files','args':{}}]

def test_due_dispatch_once_and_future(monkeypatch):
    who=owner();calls=[]
    async def create(who,command,steps): calls.append((who,command,steps));return 'task-123'
    monkeypatch.setattr(core,'create_task',create)
    sid=scheduler.create(who,'list project',STEPS,time.time()-1)
    future=scheduler.create(who,'later',STEPS,time.time()+3600)
    async def run():
        await scheduler.dispatch_due();await scheduler.dispatch_due()
    asyncio.run(run())
    assert len(calls)==1
    items={r['id']:r for r in scheduler.list_for(who)}
    assert items[sid]['status']=='dispatched' and items[sid]['task_id']=='task-123'
    assert items[future]['status']=='pending'
    db.write('DELETE FROM schedules WHERE owner=?',(who,))

def test_stopped_owner_waits_resume_dispatch(monkeypatch):
    who=owner();calls=[]
    async def create(*args): calls.append(args);return 'task-resumed'
    monkeypatch.setattr(core,'create_task',create)
    db.write('INSERT INTO flags VALUES(?,1)',(who,))
    scheduler.create(who,'list',STEPS,time.time()-1)
    asyncio.run(scheduler.dispatch_due())
    assert not calls and scheduler.list_for(who)[0]['status']=='pending'
    db.write('UPDATE flags SET stopped=0 WHERE owner=?',(who,))
    asyncio.run(scheduler.dispatch_due())
    assert len(calls)==1 and scheduler.list_for(who)[0]['status']=='dispatched'
    db.write('DELETE FROM schedules WHERE owner=?',(who,))

def test_owner_isolation_encryption_and_claim_recovery():
    a,b=owner(),owner()
    sid=scheduler.create(a,'private command',STEPS,time.time()+3600)
    assert scheduler.list_for(b)==[]
    try: scheduler.delete(b,sid)
    except LookupError: pass
    else: raise AssertionError('Other owner deleted schedule')
    raw=db.query('SELECT command,steps FROM schedules WHERE id=?',(sid,))[0]
    assert 'private' not in raw['command'] and 'list_files' not in raw['steps']
    db.write("UPDATE schedules SET status='claimed' WHERE id=?",(sid,))
    scheduler.recover()
    assert scheduler.list_for(a)[0]['status']=='interrupted'
    db.write('DELETE FROM schedules WHERE id=?',(sid,))

def test_schedule_api_timezone_validation_and_delete(monkeypatch):
    monkeypatch.setenv('GRIM_ALLOW_REGISTRATION','1')
    c=TestClient(app)
    token=c.post('/api/auth/register',json={'email':owner()+'@example.test','password':'long-scheduler-password'}).json()['token']
    headers={'Authorization':'Bearer '+token}
    bad=c.post('/api/schedules',headers=headers,json={'command':'list','steps':STEPS,'run_at':'2099-01-01T12:00:00'})
    assert bad.status_code==422
    good=c.post('/api/schedules',headers=headers,json={'command':'list','steps':STEPS,'run_at':'2099-01-01T12:00:00Z'})
    assert good.status_code==200,good.text
    sid=good.json()['id']
    assert c.get('/api/schedules',headers=headers).json()[0]['id']==sid
    assert c.delete('/api/schedules/'+sid,headers=headers).status_code==200

def test_scheduler_lifespan_starts_and_stops():
    # Entering/exiting runs startup recovery, worker creation and cancellation.
    with TestClient(app) as client:
        assert client.get('/health').json()['status']=='ok'
