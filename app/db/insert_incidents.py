import time
from app.db.dal import record_incident   # import your DAL function

# Incidents to insert
incidents = [
    {
        "incident_id": "INC001",
        "status": "OPEN",
        "service": "user-service",
        "environment": "production",
        "severity": "CRITICAL",
        "payload": {"source": "jwt-validation", "spike_percentage": 50},
        "created_at": "2025-09-27T20:30:25Z"
    },
    {
        "incident_id": "INC002",
        "status": "OPEN",
        "service": "payment-gateway",
        "environment": "production",
        "severity": "CRITICAL",
        "payload": {"source": "ssl-certificate", "spike_percentage": 100},
        "created_at": "2025-09-27T15:45:00Z"
    },
    {
        "incident_id": "INC003",
        "status": "OPEN",
        "service": "fraud-service",
        "environment": "production",
        "severity": "HIGH",
        "payload": {"source": "fraud-detection", "spike_percentage": 40},
        "created_at": "2025-09-27T14:30:25Z"
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
