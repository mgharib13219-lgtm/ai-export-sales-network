import json
import sqlite3
from pathlib import Path

from .settings import settings

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'export_sales.db'

def _db_path():
    url = settings.database_url or ''
    if url.startswith('sqlite:///'):
        raw = url[len('sqlite:///'):]
        p = Path(raw)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_PATH

DB_PATH = _db_path()
LEAD_STAGES = ('discovered','verified','matched','contacted','replied','rfq','negotiation','won','lost','repeat')
TERMINAL_STAGES = ('won','lost','repeat')

def _is_postgres():
    return (settings.database_url or '').startswith(('postgres://', 'postgresql://'))

def _con():
    if settings.environment.lower() == 'production' and not _is_postgres():
        raise RuntimeError('Production requires DATABASE_URL to be PostgreSQL')
    if _is_postgres():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError('PostgreSQL requires psycopg[binary]') from exc
        con = psycopg.connect(settings.database_url, row_factory=dict_row)
        return con
    con=sqlite3.connect(DB_PATH)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con

def _execute(con, sql, params=()):
    if _is_postgres():
        sql = sql.replace('?', '%s')
    return con.execute(sql, params)

def init_db():
    con=_con()
    if _is_postgres():
        con.execute('''CREATE TABLE IF NOT EXISTS opportunities (
          id BIGSERIAL PRIMARY KEY, product_name TEXT NOT NULL, country TEXT,
          buyer TEXT, score DOUBLE PRECISION, status TEXT DEFAULT 'new', payload TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS leads (
          id BIGSERIAL PRIMARY KEY, opportunity_id BIGINT, company_name TEXT,
          domain TEXT, country TEXT, email TEXT, phone TEXT, stage TEXT DEFAULT 'discovered',
          score DOUBLE PRECISION DEFAULT 0, next_follow_up TIMESTAMP, last_contacted_at TIMESTAMP,
          payload TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(domain, country), FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS activities (
          id BIGSERIAL PRIMARY KEY, lead_id BIGINT, kind TEXT, subject TEXT,
          body TEXT, status TEXT DEFAULT 'draft', occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(lead_id) REFERENCES leads(id)
        )''')
    else:
        con.execute('''CREATE TABLE IF NOT EXISTS opportunities (
          id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT NOT NULL, country TEXT,
          buyer TEXT, score REAL, status TEXT DEFAULT 'new', payload TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS leads (
          id INTEGER PRIMARY KEY AUTOINCREMENT, opportunity_id INTEGER, company_name TEXT,
          domain TEXT, country TEXT, email TEXT, phone TEXT, stage TEXT DEFAULT 'discovered',
          score REAL DEFAULT 0, next_follow_up DATETIME, last_contacted_at DATETIME,
          payload TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(domain, country), FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
        )''')
        con.execute('''CREATE TABLE IF NOT EXISTS activities (
          id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, kind TEXT, subject TEXT,
          body TEXT, status TEXT DEFAULT 'draft', occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(lead_id) REFERENCES leads(id)
        )''')
    con.commit(); con.close()

def add_opportunity(row):
    con=_con()
    cur=_execute(con,'INSERT INTO opportunities(product_name,country,buyer,score,status,payload) VALUES(?,?,?,?,?,?)',
        (row.get('product_name',''),row.get('country',''),row.get('buyer',''),row.get('score',0),row.get('status','new'),json.dumps(row,ensure_ascii=False,default=str)))
    rid=cur.fetchone()['id'] if _is_postgres() else cur.lastrowid
    con.commit(); con.close(); return rid

def list_opportunities(limit=100):
    con=_con(); rows=[dict(x) for x in _execute(con,'SELECT * FROM opportunities ORDER BY id DESC LIMIT ?', (limit,)).fetchall()]; con.close(); return rows

def upsert_lead(row, opportunity_id=None):
    con=_con(); domain=(row.get('domain') or '').lower().strip(); country=row.get('market') or row.get('country') or ''
    contact=row.get('contact') or {}
    email=(contact.get('emails') or [None])[0]
    phone=(contact.get('phones') or [None])[0]
    score=row.get('match_score') or (row.get('verification') or {}).get('score',0) or 0
    company=row.get('company_name') or (row.get('verification') or {}).get('company_name') or row.get('title') or ''
    existing=_execute(con,'SELECT id,stage FROM leads WHERE domain=? AND country=?',(domain,country)).fetchone() if domain else None
    payload=json.dumps(row,ensure_ascii=False,default=str)
    if existing:
        _execute(con,'''UPDATE leads SET opportunity_id=COALESCE(?,opportunity_id), company_name=COALESCE(NULLIF(?,''),company_name),
          email=COALESCE(?,email), phone=COALESCE(?,phone), score=?, payload=?, updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (opportunity_id,company,email,phone,score,payload,existing['id']))
        lid=existing['id']
    else:
        initial='matched' if score>=60 else 'verified'
        insert_sql='''INSERT INTO leads(opportunity_id,company_name,domain,country,email,phone,stage,score,payload) VALUES(?,?,?,?,?,?,?,?,?)'''
        if _is_postgres(): insert_sql += ' RETURNING id'
        cur=_execute(con,insert_sql,(opportunity_id,company,domain,country,email,phone,initial,score,payload))
        lid=cur.fetchone()['id'] if _is_postgres() else cur.lastrowid
    con.commit(); con.close(); return lid

def list_leads(stage=None, limit=200):
    con=_con()
    if stage: rows=_execute(con,'SELECT * FROM leads WHERE stage=? ORDER BY score DESC,id DESC LIMIT ?',(stage,limit)).fetchall()
    else: rows=_execute(con,'SELECT * FROM leads ORDER BY score DESC,id DESC LIMIT ?',(limit,)).fetchall()
    out=[dict(x) for x in rows]; con.close(); return out

def get_lead(lead_id):
    con=_con(); row=_execute(con,'SELECT * FROM leads WHERE id=?',(lead_id,)).fetchone(); con.close(); return dict(row) if row else None

def update_lead(lead_id, stage=None, next_follow_up=None, last_contacted_at=None):
    fields=[]; vals=[]
    if stage is not None: fields.append('stage=?'); vals.append(stage)
    if next_follow_up is not None: fields.append('next_follow_up=?'); vals.append(next_follow_up)
    if last_contacted_at is not None: fields.append('last_contacted_at=?'); vals.append(last_contacted_at)
    if not fields: return False
    fields.append('updated_at=CURRENT_TIMESTAMP'); vals.append(lead_id)
    con=_con(); cur=_execute(con,f'UPDATE leads SET {",".join(fields)} WHERE id=?',vals); con.commit(); con.close(); return cur.rowcount>0

def add_activity(lead_id, kind, subject='', body='', status='draft'):
    con=_con(); insert_sql='INSERT INTO activities(lead_id,kind,subject,body,status) VALUES(?,?,?,?,?)'
    if _is_postgres(): insert_sql += ' RETURNING id'
    cur=_execute(con,insert_sql,(lead_id,kind,subject,body,status)); rid=cur.fetchone()['id'] if _is_postgres() else cur.lastrowid; con.commit(); con.close(); return rid

def list_activities(lead_id, limit=100):
    con=_con(); rows=[dict(x) for x in _execute(con,'SELECT * FROM activities WHERE lead_id=? ORDER BY id DESC LIMIT ?',(lead_id,limit)).fetchall()]; con.close(); return rows

def due_followups(limit=100):
    con=_con(); rows=_execute(con,"SELECT * FROM leads WHERE next_follow_up IS NOT NULL AND next_follow_up <= CURRENT_TIMESTAMP AND stage NOT IN ('won','lost','repeat') ORDER BY next_follow_up LIMIT ?",(limit,)).fetchall(); out=[dict(x) for x in rows]; con.close(); return out

def crm_stats():
    con=_con()
    total=_execute(con,'SELECT COUNT(*) c FROM leads').fetchone()['c']
    rows=_execute(con,'SELECT stage,COUNT(*) c FROM leads GROUP BY stage').fetchall()
    due=_execute(con,"SELECT COUNT(*) c FROM leads WHERE next_follow_up IS NOT NULL AND next_follow_up <= CURRENT_TIMESTAMP AND stage NOT IN ('won','lost','repeat')").fetchone()['c']
    contacted=_execute(con,"SELECT COUNT(*) c FROM leads WHERE stage NOT IN ('discovered','verified','matched')").fetchone()['c']
    con.close()
    by_stage={r['stage']:r['c'] for r in rows}
    return {'total':total,'due_followups':due,'contacted_or_beyond':contacted,'by_stage':by_stage}
