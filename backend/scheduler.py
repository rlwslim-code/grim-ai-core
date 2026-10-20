"""Persistent one-shot schedules; single-process worker, fail-safe interrupted claims."""
import asyncio
import json
import time
from . import db, core

db.write('''CREATE TABLE IF NOT EXISTS schedules (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, command TEXT NOT NULL,
 steps TEXT NOT NULL, run_at REAL NOT NULL, status TEXT NOT NULL,
 task_id TEXT, error TEXT, created REAL NOT NULL)''')

def validate_steps(steps):
    if not isinstance(steps,list) or not 1<=len(steps)<=12:
        raise ValueError('Schedules require 1–12 explicit structured steps')
    if len(json.dumps(steps))>300000: raise ValueError('Plan exceeds size limit')
    names={r['name'] for r in core._executor.registry()}
    for step in steps:
        if not isinstance(step,dict) or set(step)-{'tool','args'} or step.get('tool') not in names or not isinstance(step.get('args',{}),dict):
            raise ValueError('Invalid tool plan')

def create(owner,command,steps,run_at):
    validate_steps(steps)
    with db.lock:
        if len(db.query("SELECT id FROM schedules WHERE owner=? AND status='pending'",(owner,)))>=20:
            raise ValueError('Maximum twenty pending schedules per account')
        sid=db.uid()
        db.write('INSERT INTO schedules VALUES(?,?,?,?,?,?,?,?,?)',
                 (sid,owner,db.seal(command),db.seal(json.dumps(steps)),run_at,'pending',None,None,time.time()))
    db.audit(owner,'schedule.created',sid)
    return sid

def list_for(owner):
    rows=db.query('SELECT id,command,steps,run_at,status,task_id,error,created FROM schedules WHERE owner=? ORDER BY run_at',(owner,))
    return [dict(r,command=db.unseal(r['command']),steps=json.loads(db.unseal(r['steps']))) for r in rows]

def delete(owner,sid):
    with db.lock:
        rows=db.query('SELECT status FROM schedules WHERE id=? AND owner=?',(sid,owner))
        if not rows: raise LookupError('Schedule not found')
        if rows[0]['status']!='pending': raise ValueError('Only pending schedules can be deleted')
        db.write('DELETE FROM schedules WHERE id=? AND owner=?',(sid,owner))
    db.audit(owner,'schedule.deleted',sid)

def recover():
    # A crash between claim and recording dispatch must never duplicate an action.
    db.write("UPDATE schedules SET status='interrupted',error='Worker stopped after claim; inspect task history before rescheduling' WHERE status='claimed'")

async def dispatch_due(now=None):
    rows=db.query("SELECT * FROM schedules WHERE status='pending' AND run_at<=? ORDER BY run_at LIMIT 100",(now if now is not None else time.time(),))
    for row in rows:
        owner=row['owner']
        if core.stopped(owner): continue
        if len(db.query("SELECT id FROM tasks WHERE owner=? AND status IN ('queued','running')",(owner,)))>=4: continue
        with db.lock:
            current=db.query('SELECT status FROM schedules WHERE id=?',(row['id'],))
            if not current or current[0]['status']!='pending': continue
            db.write("UPDATE schedules SET status='claimed' WHERE id=? AND status='pending'",(row['id'],))
        try:
            tid=await core.create_task(owner,db.unseal(row['command']),json.loads(db.unseal(row['steps'])))
            db.write("UPDATE schedules SET status='dispatched',task_id=? WHERE id=?",(tid,row['id']))
            db.audit(owner,'schedule.dispatched',row['id'])
        except asyncio.CancelledError:
            # Keep claimed; restart marks it interrupted, without replay.
            raise
        except PermissionError:
            db.write("UPDATE schedules SET status='pending' WHERE id=?",(row['id'],))
        except Exception:
            # No prompt or tool arguments appear in error metadata.
            db.write("UPDATE schedules SET status='failed',error='Dispatch failed; inspect configuration and task history' WHERE id=?",(row['id'],))

async def worker():
    while True:
        await dispatch_due()
        await asyncio.sleep(1)
