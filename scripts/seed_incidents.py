import json
from sqlalchemy import create_engine, text
from app.db.dal import init_db
from app.config import DB_URL

engine = create_engine(DB_URL, future=True)
init_db()

def seed_one(service='payment-service', env='prod', alert_type='db-conn-refused', severity='high'):
    payload = {"alert":"2025-09-27-seed","details":"synthetic cloudwatch-like alert","service":service}
    with engine.begin() as conn:
        conn.execute(text('INSERT INTO incidents(status,source,service,environment,alert_type,severity,payload_json) VALUES(:s,:src,:svc,:env,:at,:sev,:p)'),
            {'s':'OPEN','src':'cloudwatch_sim','svc':service,'env':env,'at':alert_type,'sev':severity,'p':json.dumps(payload)})
    print('Inserted OPEN incident for', service, env, alert_type)

if __name__ == '__main__':
    seed_one()
