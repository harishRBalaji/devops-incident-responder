import sqlite3
import time
import json
import pathlib
from app.agents.agent import run_agent
from app.db.dal import mark_in_progress, mark_done

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]  # go up from middleware/ → app/
DB_FILE = BASE_DIR / "db" / "dev.db"
POLL_INTERVAL = 10  # check every 10 seconds

def fetch_new_incidents(conn, last_seen_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE id > ? ORDER BY id ASC", (last_seen_id,))
    rows = cursor.fetchall()
    return rows

def main():
    conn = sqlite3.connect(DB_FILE)
    last_seen_id = 0  # start from the beginning (change if you only want new ones)

    print("🔎 Watching for new incidents... (Ctrl+C to stop)")

    while True:
        new_incidents = fetch_new_incidents(conn, last_seen_id)
        if new_incidents:
            for row in new_incidents:
                print("🚨 New Incident:", row)
                last_seen_id = row[0]  # update last seen ID
                incident = json.loads(row[5]) # payload json

                incident_json = {
                    "incident_id": last_seen_id,
                    "source": incident["source"],
                    "spike_percentage": incident["spike_percentage"]
                }
                mark_in_progress(incident_id=last_seen_id)
                run_agent(incident_json)
                mark_done(incident_id=last_seen_id)
    
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
