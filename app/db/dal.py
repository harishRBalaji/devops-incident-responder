from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import DB_URL

engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, future=True)

def init_db():
    with engine.begin() as conn:
        with open('app/db/schema.sql','r',encoding='utf-8') as f:
            conn.executescript = getattr(conn, 'executescript', None)
            sql = f.read()
            for stmt in sql.split(';'):
                if stmt.strip():
                    conn.execute(text(stmt))

def get_open_incidents():
    with engine.begin() as conn:
        res = conn.execute(text('SELECT * FROM incidents WHERE status = :s ORDER BY id ASC'), {'s':'OPEN'})
        return [dict(r._mapping) for r in res]

def mark_in_progress(incident_id:int):
    with engine.begin() as conn:
        conn.execute(text('UPDATE incidents SET status=:s WHERE id=:id'), {'s':'IN_PROGRESS','id':incident_id})

def mark_done(incident_id:int):
    with engine.begin() as conn:
        conn.execute(text('UPDATE incidents SET status=:s WHERE id=:id'), {'s':'DONE','id':incident_id})

def mark_failed(incident_id:int):
    with engine.begin() as conn:
        conn.execute(text('UPDATE incidents SET status=:s WHERE id=:id'), {'s':'FAILED','id':incident_id})

def record_step(incident_id:int, agent:str, phase:str, message:str, data:dict=None):
    import json, datetime
    with engine.begin() as conn:
        conn.execute(text('INSERT INTO agent_steps(incident_id,agent,phase,message,data_json) VALUES(:i,:a,:p,:m,:d)'),
                     {'i':incident_id,'a':agent,'p':phase,'m':message,'d':json.dumps(data or {})})

def save_report(incident_id:int, report_json:dict, report_md:str):
    import json
    with engine.begin() as conn:
        conn.execute(text('INSERT INTO reports(incident_id,report_json,report_md) VALUES(:i,:j,:m)'),
                     {'i':incident_id,'j':json.dumps(report_json),'m':report_md})
