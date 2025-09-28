# app/middleware/poll_incidents.py
import sqlite3
import time
import json
import os
from app.agents.agent import run_agent
from app.db.dal import mark_in_progress, mark_done

# Use the same DB file as dal.py (from env or default to dev.db)
DB_FILE = os.environ.get("DB_FILE", "dev.db")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "10"))

def fetch_new_incidents(conn, last_seen_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE id > ? ORDER BY id ASC", (last_seen_id,))
    rows = cursor.fetchall()
    return rows

def main():
    conn = sqlite3.connect(DB_FILE)
    last_seen_id = 0  # start from the beginning

    print(f"🔎 Watching for new incidents in {DB_FILE}... (Ctrl+C to stop)")

    while True:
        new_incidents = fetch_new_incidents(conn, last_seen_id)
        if new_incidents:
            for row in new_incidents:
                print("🚨 New Incident:", row)
                last_seen_id = row[0]  # assumes first column is the incident id
                incident = json.loads(row[5])  # payload_json is 6th column

                incident_json = {
                    "incident_id": last_seen_id,
                    "source": incident.get("source"),
                    "spike_percentage": incident.get("spike_percentage")
                }

                mark_in_progress(incident_id=last_seen_id)
                run_agent(incident_json)
                mark_done(incident_id=last_seen_id)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
