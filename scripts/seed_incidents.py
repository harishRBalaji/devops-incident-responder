import time
from app.db.dal import record_incident   # correct import

# Incidents to insert
incidents = [
    {
        "incident_id": "INC001",
        "status": "OPEN",
        "service": "checkout-service",
        "environment": "production",
        "severity": "CRITICAL",
        "payload": {"source": "db-connection-pool", "spike_percentage": 100},
        "created_at": "2025-09-27T15:09:00Z"
    },
    {
        "incident_id": "INC002",
        "status": "OPEN",
        "service": "inventory-service",
        "environment": "production",
        "severity": "HIGH",
        "payload": {"source": "slow-query-lock", "spike_percentage": 35},
        "created_at": "2025-09-27T15:08:00Z"
    },
    {
        "incident_id": "INC003",
        "status": "OPEN",
        "service": "orders-service",
        "environment": "production",
        "severity": "CRITICAL",
        "payload": {"source": "deadlock-cascade", "spike_percentage": 102},
        "created_at": "2025-09-27T15:08:00Z"
    }
]

if __name__ == "__main__":
    for inc in incidents:
        incident_id = record_incident(
            incident_id=inc["incident_id"],
            status=inc["status"],
            service=inc["service"],
            environment=inc["environment"],
            severity=inc["severity"],
            payload=inc["payload"],
            created_at=inc["created_at"]
        )
        print(f"✅ Inserted incident with id={incident_id}")
        time.sleep(30)  # wait 30 seconds before next insert
