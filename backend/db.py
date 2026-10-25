import os, sqlite3, threading, time, uuid
from pathlib import Path
from cryptography.fernet import Fernet

ROOT = Path(os.getenv('GRIM_DATA_DIR', './data')).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(ROOT, 0o700)
except PermissionError:
    pass
keypath = ROOT / 'memory.key'
if not keypath.exists():
    fd = os.open(keypath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f: f.write(Fernet.generate_key())
cipher = Fernet(keypath.read_bytes())
lock = threading.RLock()
conn = sqlite3.connect(ROOT / 'grim.sqlite3', check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.executescript('''
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,owner TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,conversation TEXT NOT NULL,owner TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS memory(id TEXT PRIMARY KEY,owner TEXT NOT NULL,kind TEXT NOT NULL,content TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,owner TEXT NOT NULL,command TEXT NOT NULL,status TEXT NOT NULL,result TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,owner TEXT NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS flags(owner TEXT PRIMARY KEY,stopped INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS companion_preferences(owner TEXT PRIMARY KEY, relationship_style TEXT NOT NULL DEFAULT 'neutral', memory_enabled INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS companion_memories(id TEXT PRIMARY KEY, owner TEXT NOT NULL, content TEXT NOT NULL, created REAL NOT NULL);
''')
conn.commit()

def query(sql, args=()):
    with lock: return [dict(x) for x in conn.execute(sql,args).fetchall()]

def write(sql,args=()):
    with lock:
        conn.execute(sql,args); conn.commit()

def uid(): return uuid.uuid4().hex

def seal(value): return cipher.encrypt(value.encode()).decode()
def unseal(value): return cipher.decrypt(value.encode()).decode()
def audit(owner,action,detail=''):
    # Audit only operation metadata; never prompt text, tokens, or command output.
    write('INSERT INTO audit VALUES(?,?,?,?,?)',(uid(),owner,action,detail[:300],time.time()))
