# app/db/dal.py
import os, sqlite3, json, datetime, pathlib
from typing import Any, Dict, Optional, List

DB_FILE = os.environ.get("DB_FILE", "dev.db")
SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"

def _now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _conn(rowdict: bool = False) -> sqlite3.Connection:
    con = sqlite3.connect(DB_FILE)
    con.execute("PRAGMA foreign_keys = ON")
    if rowdict:
        con.row_factory = sqlite3.Row
    return con

def init_db() -> None:
    """Create all tables from schema.sql (idempotent)."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with _conn() as con:
        con.executescript(sql)

def _ensure_schema() -> None:
    """Ensure required tables exist (safe to call at import)."""
    required = {"incidents", "agent_steps", "reports"}
    with _conn() as con:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        have = {r[0] for r in rows}
        if not required.issubset(have):
            sql = SCHEMA_PATH.read_text(encoding="utf-8")
            con.executescript(sql)

_ensure_schema()
# ---------- writes ----------

def record_incident(
    incident_id: str,            # required, like "INC001"
    status: str,                 # "OPEN" | "IN_PROGRESS" | "DONE" | "FAILED"
    service: str,
    environment: str,
    severity: str,
    payload: Dict[str, Any] | None = None,
    created_at: str | None = None,
) -> str:
    """Insert a new incident and return its id (must be provided)."""
    with _conn() as con:
        con.execute(
            """INSERT INTO incidents(id, status, service, environment, severity, payload_json, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                incident_id,
                status,
                service,
                environment,
                severity,
                json.dumps(payload or {}),
                created_at or _now_iso(),
            ),
        )
    return incident_id

def record_step(
    incident_id: int,
    phase_title: str,
    message: str,
    phase: str = "in_progress"
) -> None:
    """
    Insert a new step into agent_steps and return its row id.
    phase: "in_progress" | "complete" | "error"
    """
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO agent_steps(incident_id, phase_title, message, phase, ts)
               VALUES(?,?,?,?,?)""",
            (incident_id, phase_title, message, phase, _now_iso())
        )
        return cur.lastrowid


def update_step_status(step_id: int, new_phase: str) -> None:
    """Update the phase of a step (e.g., from in_progress → complete)."""
    with _conn() as con:
        con.execute(
            """UPDATE agent_steps SET phase=? WHERE id=?""",
            (new_phase, step_id)
        )

def save_report(incident_id: int, report_text: str) -> None:
    """Save a full incident report (as text blob) into the reports table."""
    with _conn() as con:
        con.execute(
            """INSERT INTO reports(incident_id, report_json, created_at)
               VALUES(?,?,?)""",
            (incident_id, report_text, _now_iso())
        )

# ---------- reads (for UI) ----------

def list_incidents(limit: int = 200) -> List[Dict[str, Any]]:
    sql = """SELECT id, status, service, environment, severity, created_at
             FROM incidents ORDER BY id DESC LIMIT ?"""
    with _conn(rowdict=True) as con:
        rows = con.execute(sql, (limit,)).fetchall()
    return [dict(r) for r in rows]

def get_incident(incident_id: int) -> Optional[Dict[str, Any]]:
    with _conn(rowdict=True) as con:
        r = con.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
    return dict(r) if r else None

def list_steps(incident_id: str) -> List[Dict[str, Any]]:
    sql = """SELECT id, phase_title, message, phase, ts
             FROM agent_steps WHERE incident_id=? ORDER BY id ASC"""
    with _conn(rowdict=True) as con:
        rows = con.execute(sql, (incident_id,)).fetchall()
    return [dict(r) for r in rows]

def get_latest_report(incident_id: int) -> Optional[Dict[str, Any]]:
    sql = """SELECT id, report_json, created_at
             FROM reports WHERE incident_id=? ORDER BY id DESC LIMIT 1"""
    with _conn(rowdict=True) as con:
        r = con.execute(sql, (incident_id,)).fetchone()
    if not r:
        return None

    d = dict(r)
    # Preserve the raw HTML so the UI can render it.
    # Also mirror it under "report" for backward compatibility with UIs
    # that expect "report".
    html = d.get("report_json") or ""
    d["report"] = html
    return d

# ---------- helpers for the agent loop ----------

def get_open_incidents() -> List[Dict[str, Any]]:
    with _conn(rowdict=True) as con:
        rows = con.execute("SELECT * FROM incidents WHERE status='OPEN' ORDER BY id ASC").fetchall()
    return [dict(r) for r in rows]

def mark_in_progress(incident_id: int) -> None:
    with _conn() as con:
        con.execute("UPDATE incidents SET status='IN_PROGRESS' WHERE id=?", (incident_id,))

def mark_done(incident_id: int) -> None:
    with _conn() as con:
        con.execute("UPDATE incidents SET status='DONE' WHERE id=?", (incident_id,))

def mark_failed(incident_id: int) -> None:
    with _conn() as con:
        con.execute("UPDATE incidents SET status='FAILED' WHERE id=?", (incident_id,))
