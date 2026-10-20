import asyncio, uuid
from backend import core, db

class FakeExecutor:
    def __init__(self): self.calls=[]
    def registry(self): return [{'name':'write_file'}, {'name':'pytest'}]
    async def execute(self, tool, args, owner, task_id):
        self.calls.append((tool,args))
        if tool=='pytest' and len([c for c in self.calls if c[0]=='pytest'])==1:
            return {'ok':False,'exit_code':1,'output':'test failed'}
        return {'ok':True,'exit_code':0,'output':'passed'}

async def perform(monkeypatch, repair=True):
    who=uuid.uuid4().hex; tid=uuid.uuid4().hex
    executor=FakeExecutor()
    monkeypatch.setattr(core,'_executor',executor)
    db.write('INSERT INTO tasks VALUES (?,?,?,?,?,?)',(tid,who,db.seal('fix tests'),'queued',db.seal('{}'),0))
    seen=[]
    async def propose(*args):
        seen.append(args)
        return '{"tool":"pytest","args":{}}'
    monkeypatch.setattr(core.provider,'complete',propose)
    await core.run_task(tid,who,[{'tool':'pytest','args':{}}],command='fix tests',auto_repair=repair)
    row=db.query('SELECT status,result FROM tasks WHERE id=?',(tid,))[0]
    db.write('DELETE FROM tasks WHERE id=?',(tid,))
    return row['status'], db.unseal(row['result']), executor.calls, seen

def test_autorepair_success(monkeypatch):
    state, result, calls, seen=asyncio.run(perform(monkeypatch))
    assert state=='completed'
    assert len(calls)==2 and len(seen)==1
    assert 'repair_planning' in result

def test_without_repair_fails(monkeypatch):
    state, result, calls, seen=asyncio.run(perform(monkeypatch,False))
    assert state=='failed' and len(calls)==1 and not seen

def test_rejects_unpermitted_repair(monkeypatch):
    monkeypatch.setattr(core,'_executor',FakeExecutor())
    async def rogue(*args): return '{"tool":"shell","args":{"command":"whoami"}}'
    monkeypatch.setattr(core.provider,'complete',rogue)
    async def check():
        try: await core.repair_step('goal',{'tool':'pytest','args':{}},{'error':'failed'})
        except ValueError: return True
        return False
    assert asyncio.run(check())

def test_validate_repair_schema(monkeypatch):
    monkeypatch.setattr(core,'_executor',FakeExecutor())
    for steps in ([{'tool':'pytest','args':{},'admin':True}], [{'tool':'nope','args':{}}], []):
        try: core.validate_tool_steps(steps)
        except ValueError: pass
        else: raise AssertionError('Untrusted plan passed')
