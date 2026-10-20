import json
from backend.tests.test_api import client, account
from backend import db


def test_task_event_stream_owner_isolation():
    owner=account();other=account();tid=db.uid()
    token=owner['Authorization'][7:]
    import hashlib,time
    owner_id=db.query('SELECT owner FROM sessions WHERE hash=?',(hashlib.sha256(token.encode()).hexdigest(),))[0]['owner']
    db.write('INSERT INTO tasks VALUES(?,?,?,?,?,?)',(tid,owner_id,db.seal('test'), 'completed', db.seal(json.dumps({'events':[{'ok':True}]})),time.time()))
    assert client.get('/api/tasks/'+tid+'/events',headers=other).status_code==404
    r=client.get('/api/tasks/'+tid+'/events',headers=owner)
    assert r.status_code==200
    assert '"completed"' in r.text and '"ok": true' in r.text
    assert client.get('/api/tasks/'+tid+'/events').status_code==401
