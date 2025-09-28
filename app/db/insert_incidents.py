import sqlite3
import time

# Connect to SQLite DB (change path if needed)
conn = sqlite3.connect("incidents.db")
cursor = conn.cursor()

# Ensure table exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS incidents(
  id           String PRIMARY KEY,
  status       TEXT NOT NULL,
  service      TEXT NOT NULL,
  environment  TEXT NOT NULL,
  severity     TEXT NOT NULL,
  payload_json TEXT,
  created_at   TEXT NOT NULL
);
""")

# Incidents to insert
incidents = [
    (
        "INC001",
        'OPEN',
        'user-service',
        'production',
        'CRITICAL',
        '{"source": "jwt-validation", "spike_percentage": 50}',
        '2025-09-27T20:30:25Z'
    ),
    (
        "INC002",
        'OPEN',
        'payment-gateway',
        'production',
        'CRITICAL',
        '{"source": "ssl-certificate", "spike_percentage": 100}',
        '2025-09-27T15:45:00Z'
    ),
    (
        "INC003",
        'fraud-service',
        'OPEN',
        'production',
        'HIGH',
        '{"source": "fraud-detection", "spike_percentage": 40}',
        '2025-09-27T14:30:25Z'
    )
]

# Insert rows with 30s interval
for incident in incidents:
    cursor.execute("""
    INSERT INTO incidents (id, status, service, environment, severity, payload_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, incident)
    conn.commit()
    print(f"Inserted incident {incident[0]}")
    time.sleep(30)  # wait 30 seconds

conn.close()
