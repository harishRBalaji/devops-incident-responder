-- Minimal schema
CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status TEXT NOT NULL,
  source TEXT,
  service TEXT,
  environment TEXT,
  alert_type TEXT,
  severity TEXT,
  payload_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id INTEGER NOT NULL,
  agent TEXT,
  phase TEXT,
  message TEXT,
  data_json TEXT,
  ts TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id INTEGER NOT NULL,
  report_json TEXT,
  report_md TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
