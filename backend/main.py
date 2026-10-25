import os, time, hashlib, secrets, json, asyncio, logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import db, core
from .providers import ProviderUnavailable, provider, MODES, EMOTIONS

@asynccontextmanager
async def lifespan(app):
    from . import scheduler
    db.write("UPDATE tasks SET status='interrupted' WHERE status IN ('running','queued')")
    scheduler.recover()
    worker=asyncio.create_task(scheduler.worker())
    try:
        yield
    finally:
        worker.cancel()
        await asyncio.gather(worker,return_exceptions=True)
        pending=list(core._running.values())
        for task in pending: task.cancel()
        if pending: await asyncio.gather(*pending,return_exceptions=True)
        for executor in adapter.instances.values(): await executor.stop()

app=FastAPI(title='GRIM AI — DARK GENESIS',version='1.3.1',lifespan=lifespan)
# GRIM AI — CORS configuration
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "GRIM_ALLOWED_ORIGINS",
        "http://localhost:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

class AuthBody(BaseModel):
    email: str=Field(min_length=3,max_length=254)
    password: str=Field(min_length=12,max_length=256)
class ChatBody(BaseModel):
    message: str=Field(min_length=1,max_length=16000)
    conversation_id: str|None=None
    mode: Literal['NORMAL','OBSIDIAN','BLOODLINE','ABYSS']='OBSIDIAN'
    relationship_style: Literal['neutral','friendly','affectionate']='neutral'
class MemoryBody(BaseModel):
    content: str=Field(min_length=1,max_length=32000)
    kind: str=Field(default='note',max_length=50)
class TaskBody(BaseModel):
    command: str=Field(min_length=1,max_length=16000)
    steps: list[dict]|None=None
    auto_repair: bool=False
class LabBody(BaseModel):
    action: Literal['create','stop','reset']
    id: str|None=None

attempts={}
def throttle(key):
    now=time.monotonic(); times=[t for t in attempts.get(key,[]) if now-t<60]
    if len(times)>=10: raise HTTPException(429,'Too many attempts; retry after one minute')
    attempts[key]=times+[now]
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    value=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    return salt+':'+value

def auth(authorization: str=Header(default='')):
    token=authorization.removeprefix('Bearer ')
    if not token or authorization==token: raise HTTPException(401,'Authentication required')
    rows=db.query('SELECT owner FROM sessions WHERE hash=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time()))
    if not rows: raise HTTPException(401,'Session expired or revoked')
    return rows[0]['owner']

def session(user):
    token=secrets.token_urlsafe(40)
    db.write('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],time.time()+7*86400))
    return {'token':token,'user':{'id':user['id'],'email':user['email']}}

@app.post('/api/auth/register')
def register(body:AuthBody):
    email=body.email.strip().lower();throttle('register')
    if '@' not in email: raise HTTPException(422,'Valid email required')
    if db.query('SELECT id FROM users LIMIT 1') and os.getenv('GRIM_ALLOW_REGISTRATION')!='1': raise HTTPException(403,'Registration disabled; operator must enable additional accounts')
    user={'id':db.uid(),'email':email}
    try: db.write('INSERT INTO users VALUES(?,?,?,?)',(user['id'],email,password_hash(body.password),time.time()))
    except Exception: raise HTTPException(409,'Account already exists')
    db.audit(user['id'],'auth.register')
    return session(user)

@app.post('/api/auth/login')
def login(body:AuthBody):
    email=body.email.strip().lower();throttle('login:'+email)
    rows=db.query('SELECT * FROM users WHERE email=?',(email,))
    stored=rows[0]['password'] if rows else password_hash('invalid-account-password')
    if not secrets.compare_digest(password_hash(body.password,stored.split(':')[0]),stored) or not rows: raise HTTPException(401,'Invalid credentials')
    db.audit(rows[0]['id'],'auth.login');return session(rows[0])

@app.post('/api/auth/logout')
def logout(owner=Depends(auth),authorization:str=Header(default='')):
    db.write('DELETE FROM sessions WHERE hash=?',(hashlib.sha256(authorization[7:].encode()).hexdigest(),));return {'ok':True}

@app.post('/api/auth/revoke-all')
async def revoke(owner=Depends(auth)):
    await core.stop(owner);db.write('DELETE FROM sessions WHERE owner=?',(owner,));return {'ok':True}

@app.get('/api/status')
async def status(owner=Depends(auth)):
    executor=await adapter.status(owner)
    model_health=await provider.readiness()
    return {'name':'GRIM AI','version':'1.3 — PROJECT AWAKENING','model':{'provider':'openai-compatible','model':provider.model,'configured':bool(provider.model and provider.base),'verified':model_health['model_available'],'health':model_health},'executor':executor,'stopped':core.stopped(owner),'personality':list(MODES),'emotions':EMOTIONS,'retrieval':'lexical' }

@app.get('/api/capabilities')
async def capabilities(owner=Depends(auth)):
    """Authenticated, conservative capability inventory; no speculative claims."""
    from .precision import CAPABILITIES
    return {'capabilities': CAPABILITIES, 'note': 'Status describes implemented architecture, not a live proof of successful execution.'}

class CompanionPreferencesBody(BaseModel):
    relationship_style: Literal['neutral','friendly','affectionate']='neutral'
    memory_enabled: bool=False

class CompanionMemoryBody(BaseModel):
    content: str=Field(min_length=1,max_length=2000)

@app.get('/api/companion/preferences')
def companion_preferences(owner=Depends(auth)):
    rows=db.query('SELECT relationship_style,memory_enabled FROM companion_preferences WHERE owner=?',(owner,))
    return dict(rows[0],memory_enabled=bool(rows[0]['memory_enabled'])) if rows else {'relationship_style':'neutral','memory_enabled':False}

@app.put('/api/companion/preferences')
def update_companion_preferences(body:CompanionPreferencesBody,owner=Depends(auth)):
    db.write('INSERT INTO companion_preferences(owner,relationship_style,memory_enabled,updated) VALUES(?,?,?,?) ON CONFLICT(owner) DO UPDATE SET relationship_style=excluded.relationship_style,memory_enabled=excluded.memory_enabled,updated=excluded.updated', (owner,body.relationship_style,int(body.memory_enabled),time.time()))
    db.audit(owner,'companion.preferences_updated')
    return {'relationship_style':body.relationship_style,'memory_enabled':body.memory_enabled}

@app.get('/api/companion/memories')
def companion_memories(owner=Depends(auth)):
    rows=db.query('SELECT id,content,created FROM companion_memories WHERE owner=? ORDER BY created DESC LIMIT 100',(owner,))
    return [dict(row,content=db.unseal(row['content'])) for row in rows]

@app.post('/api/companion/memories')
def add_companion_memory(body:CompanionMemoryBody,owner=Depends(auth)):
    preferences=companion_preferences(owner)
    if not preferences['memory_enabled']: raise HTTPException(403,'Companion memory is disabled')
    mid=db.uid()
    db.write('INSERT INTO companion_memories VALUES(?,?,?,?)',(mid,owner,db.seal(body.content),time.time()))
    db.audit(owner,'companion.memory_added')
    return {'id':mid}

@app.delete('/api/companion/memories/{memory_id}')
def delete_companion_memory(memory_id:str,owner=Depends(auth)):
    rows=db.query('SELECT id FROM companion_memories WHERE id=? AND owner=?',(memory_id,owner))
    if not rows: raise HTTPException(404,'Memory not found')
    db.write('DELETE FROM companion_memories WHERE id=? AND owner=?',(memory_id,owner))
    db.audit(owner,'companion.memory_deleted')
    return {'ok':True}

@app.post('/api/chat')
async def chat(body:ChatBody,owner=Depends(auth)):
    try: return await core.chat(owner,body.message,body.conversation_id,body.mode,body.relationship_style)
    except ProviderUnavailable as e: raise HTTPException(503,str(e))
    except LookupError as e: raise HTTPException(404,str(e))

stream_log = logging.getLogger('grim.stream')

@app.post('/api/chat/stream')
async def chat_stream(body:ChatBody,owner=Depends(auth)):
    if body.conversation_id and not db.query('SELECT id FROM conversations WHERE id=? AND owner=?',(body.conversation_id,owner)):
        raise HTTPException(404,'Conversation not found')
    async def events():
        try:
            async for event in core.stream_chat(owner,body.message,body.conversation_id,body.mode,body.relationship_style):
                yield 'data: '+json.dumps(event,ensure_ascii=False)+'\n\n'
        except ProviderUnavailable as exc:
            stream_log.warning('Stream provider failure: category=%s detail=%s', exc.category, str(exc))
            yield 'data: '+json.dumps({'event':'error','category':exc.category,'message':str(exc)})+'\n\n'
        except Exception:
            stream_log.exception('Unexpected GRIM streaming failure')
            yield 'data: '+json.dumps({'event':'error','category':'execution_failure','message':'Streaming request failed; inspect Render logs for traceback'})+'\n\n'
        else:
            yield 'data: '+json.dumps({'event':'done'})+'\n\n'
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.get('/api/conversations')
def conversations(owner=Depends(auth)):
    return [dict(r,title=db.unseal(r['title'])) for r in db.query('SELECT id,title,created FROM conversations WHERE owner=? ORDER BY created DESC',(owner,))]

@app.delete('/api/conversations/{cid}')
def delete_conversation(cid: str, owner=Depends(auth)):
    """Remove a conversation and its messages, scoped to the authenticated owner."""
    if not db.query('SELECT id FROM conversations WHERE id=? AND owner=?', (cid,owner)):
        raise HTTPException(404,'Conversation not found')
    with db.lock:
        db.conn.execute('DELETE FROM messages WHERE conversation=? AND owner=?',(cid,owner))
        db.conn.execute('DELETE FROM conversations WHERE id=? AND owner=?',(cid,owner))
        db.conn.commit()
    db.audit(owner,'conversation.deleted',cid)
    return {'ok':True}

@app.get('/api/workspace/export')
def workspace_export(owner=Depends(auth)):
    """Download project files as an authenticated, size-bounded ZIP; no host shell."""
    from .workspace import workspace_zip
    try: content=workspace_zip(adapter.get(owner).root)
    except ValueError as exc: raise HTTPException(422,str(exc))
    db.audit(owner,'workspace.export')
    return Response(content=content,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="grim-workspace.zip"','Cache-Control':'no-store'})

@app.post('/api/tasks/{tid}/cancel')
async def cancel_task(tid: str, owner=Depends(auth)):
    rows=db.query('SELECT status FROM tasks WHERE id=? AND owner=?',(tid,owner))
    if not rows: raise HTTPException(404,'Task not found')
    if rows[0]['status'] not in ('queued','running'):
        raise HTTPException(409,'Task is already final')
    task=core._running.get(tid)
    if task: task.cancel()
    await adapter.get(owner).stop(tid)
    if not task:
        db.write("UPDATE tasks SET status='cancelled' WHERE id=? AND owner=? AND status IN ('queued','running')",(tid,owner))
    db.audit(owner,'task.cancel.requested',tid)
    return {'ok':True,'id':tid}

@app.get('/api/conversations/{cid}')
def messages(cid:str,owner=Depends(auth)):
    if not db.query('SELECT id FROM conversations WHERE id=? AND owner=?',(cid,owner)): raise HTTPException(404,'Conversation not found')
    return [dict(r,content=db.unseal(r['content'])) for r in db.query('SELECT id,role,content,created FROM messages WHERE conversation=? AND owner=? ORDER BY created',(cid,owner))]

@app.get('/api/memory')
def memories(q:str='',owner=Depends(auth)):
    if q: return core.memory_search(owner,q)
    return [dict(r,content=db.unseal(r['content'])) for r in db.query('SELECT id,kind,content,created FROM memory WHERE owner=? ORDER BY created DESC',(owner,))]

@app.get('/api/memory/search')
async def search_memory(q:str,owner=Depends(auth)):
    return await core.retrieve(owner,q)

@app.post('/api/memory')
def add_memory(body:MemoryBody,owner=Depends(auth)):
    throttle('memory:'+owner)
    item={'id':db.uid(),'kind':body.kind,'content':body.content,'created':time.time()}
    db.write('INSERT INTO memory VALUES(?,?,?,?,?)',(item['id'],owner,item['kind'],db.seal(item['content']),item['created']));return item

@app.put('/api/memory/{mid}')
def update_memory(mid:str,body:MemoryBody,owner=Depends(auth)):
    if not db.query('SELECT id FROM memory WHERE id=? AND owner=?',(mid,owner)): raise HTTPException(404,'Memory not found')
    db.write('UPDATE memory SET content=?,kind=? WHERE id=? AND owner=?',(db.seal(body.content),body.kind,mid,owner));return {'ok':True}

@app.delete('/api/memory/{mid}')
def delete_memory(mid:str,owner=Depends(auth)):
    db.write('DELETE FROM memory WHERE id=? AND owner=?',(mid,owner));return {'ok':True}

def task_decode(r): return dict(r,command=db.unseal(r['command']),result=json.loads(db.unseal(r['result'])))
@app.get('/api/tasks')
def tasks(owner=Depends(auth)):
    return [task_decode(r) for r in db.query('SELECT id,command,status,result,created FROM tasks WHERE owner=? ORDER BY created DESC LIMIT 100',(owner,))]

@app.get('/api/tasks/{tid}')
def get_task(tid:str,owner=Depends(auth)):
    rows=db.query('SELECT id,command,status,result,created FROM tasks WHERE id=? AND owner=?',(tid,owner))
    if not rows: raise HTTPException(404,'Task not found')
    return task_decode(rows[0])

@app.get('/api/tasks/{tid}/events')
async def task_events(tid: str, owner=Depends(auth)):
    """Read-only authenticated task progress stream; source is persisted execution state."""
    def snapshot():
        rows=db.query('SELECT id,status,result FROM tasks WHERE id=? AND owner=?',(tid,owner))
        if not rows: raise HTTPException(404,'Task not found')
        row=rows[0]
        return {'id':row['id'],'status':row['status'],'result':json.loads(db.unseal(row['result']))}
    snapshot()  # Reject other users before opening the stream.
    async def events():
        previous=None
        for _ in range(300):
            data=snapshot()
            encoded=json.dumps(data,ensure_ascii=False)
            if encoded!=previous:
                yield 'data: '+encoded+'\n\n'
                previous=encoded
            if data['status'] in ('completed','failed','interrupted','cancelled'):
                break
            await asyncio.sleep(1)
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.post('/api/tasks')
async def task(body:TaskBody,owner=Depends(auth)):
    throttle('task:'+owner)
    try: return {'id':await core.create_task(owner,body.command,body.steps,auto_repair=body.auto_repair),'status':'queued'}
    except ProviderUnavailable as e: raise HTTPException(503,str(e))
    except PermissionError as e: raise HTTPException(423,str(e))
    except (ValueError,TypeError,KeyError) as e: raise HTTPException(422,str(e))

@app.post('/api/emergency-stop')
async def stop(owner=Depends(auth)):
    await core.stop(owner);return {'stopped':True}

@app.post('/api/resume')
def resume(owner=Depends(auth)):
    db.write('INSERT INTO flags VALUES(?,0) ON CONFLICT(owner) DO UPDATE SET stopped=0',(owner,));adapter.resume(owner);db.audit(owner,'emergency.resume');return {'stopped':False}

@app.get('/api/tools')
def tools(owner=Depends(auth)): return adapter.registry()

@app.get('/api/audit')
def audits(owner=Depends(auth)): return db.query('SELECT action,detail,created FROM audit WHERE owner=? ORDER BY created DESC LIMIT 200',(owner,))

@app.get('/health')
def health(): return {'status':'ok','service':'GRIM AI'}

from .executor import Executor, TOOLS
from .labs import LabManager, discover_tools
class ExecutorAdapter:
    def __init__(self): self.instances={};self.labs={}
    def get(self,owner):
        if owner not in self.instances: self.instances[owner]=Executor(db.ROOT/'workspaces'/owner)
        return self.instances[owner]
    def lab(self,owner):
        if owner not in self.labs: self.labs[owner]=LabManager(namespace=owner)
        return self.labs[owner]
    def registry(self): return [dict(name=k,**v) for k,v in TOOLS.items()]
    async def execute(self,tool,args,owner,task_id): return await self.get(owner).execute(tool,args,task_id)
    async def stop_all(self,owner):
        await self.get(owner).stop()
        await self.lab(owner).stop()
    def resume(self,owner): self.get(owner).resume()
    async def status(self,owner):
        lab=await self.lab(owner).status()
        return {'state':'available' if lab['state']!='unavailable' else 'partial','sandbox':lab,'tools':self.registry()}
adapter=ExecutorAdapter();core.set_executor(adapter)

from . import shadow

class ArtifactBody(BaseModel):
    data_base64: str = Field(min_length=1, max_length=shadow.MAX_ARTIFACT * 4 // 3 + 8)

@app.get('/api/shadow/status')
async def shadow_status(owner=Depends(auth)):
    return {'gateway': await shadow.tor_gateway(), 'arsenal': shadow.arsenal(),
            'execution_policy': 'read-only diagnostics', 'laboratory': await adapter.lab(owner).status()}

@app.post('/api/shadow/inspect')
async def shadow_inspect(body: ArtifactBody, owner=Depends(auth)):
    if core.stopped(owner): raise HTTPException(423, 'Emergency stop is active')
    try: result = shadow.inspect_artifact(body.data_base64)
    except ValueError as error: raise HTTPException(422, str(error))
    db.audit(owner, 'shadow.static_inspect', json.dumps({'sha256': result['sha256'], 'bytes': result['size_bytes']}))
    return result

@app.get('/api/labs')
async def labs(owner=Depends(auth)):
    return {'lab':await adapter.lab(owner).status(),'tools':discover_tools()}

@app.post('/api/labs')
async def lab_action(body:LabBody,owner=Depends(auth)):
    if core.stopped(owner) and body.action!='stop': raise HTTPException(423,'Emergency stop is active')
    result=await getattr(adapter.lab(owner),body.action)();db.audit(owner,'lab.'+body.action);return result

from . import scheduler
class ScheduleBody(BaseModel):
    command: str=Field(min_length=1,max_length=16000)
    steps: list[dict]
    run_at: datetime

@app.post('/api/schedules')
def create_schedule(body:ScheduleBody,owner=Depends(auth)):
    throttle('schedule:'+owner)
    if body.run_at.tzinfo is None or body.run_at.utcoffset() is None:
        raise HTTPException(422,'run_at requires an explicit timezone offset')
    try:
        sid=scheduler.create(owner,body.command,body.steps,body.run_at.timestamp())
        return {'id':sid,'status':'pending'}
    except ValueError as e: raise HTTPException(422,str(e))

@app.get('/api/schedules')
def schedules(owner=Depends(auth)): return scheduler.list_for(owner)

@app.delete('/api/schedules/{sid}')
def delete_schedule(sid:str,owner=Depends(auth)):
    try: scheduler.delete(owner,sid);return {'ok':True}
    except LookupError as e: raise HTTPException(404,str(e))
    except ValueError as e: raise HTTPException(409,str(e))

web_dist=Path(__file__).resolve().parent.parent/'web'/'dist'
if web_dist.exists(): app.mount('/',StaticFiles(directory=str(web_dist),html=True),name='web')
