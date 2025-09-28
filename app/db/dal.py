# app/db/dal.py
import os, sqlite3, json, datetime, pathlib
from typing import Any, Dict, Optional, List

DB_FILE = os.environ.get("DB_FILE", "dev.db")

def _now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _conn(rowdict: bool = False) -> sqlite3.Connection:
    con = sqlite3.connect(DB_FILE)
    con.execute("PRAGMA foreign_keys = ON")
    if rowdict:
        con.row_factory = sqlite3.Row
    return con

def init_db() -> None:
    sql = pathlib.Path("schema.sql").read_text(encoding="utf-8")
    with _conn() as con:
        con.executescript(sql)

# ---------- writes ----------

def record_incident(
    status: str,                 # "OPEN" | "IN_PROGRESS" | "DONE" | "FAILED"
    service: str,
    environment: str,
    severity: str,
    payload: Dict[str, Any] | None = None,
    created_at: str | None = None,
    incident_id: str | None = None
) -> int:
    """Insert a new incident and return its id."""
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO incidents(id, status, service, environment, severity, payload_json, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                incident_id,                       # None → auto id
                status,
                service,
                environment,
                severity,
                json.dumps(payload or {}),
                created_at or _now_iso(),
            ),
        )
        return incident_id if incident_id is not None else cur.lastrowid

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

def list_steps(incident_id: int) -> List[Dict[str, Any]]:
    sql = """SELECT id, agent, phase, status, message, ts, data_json
             FROM agent_steps WHERE incident_id=? ORDER BY id ASC"""
    with _conn(rowdict=True) as con:
        rows = con.execute(sql, (incident_id,)).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        try:
            d["data"] = json.loads(d.pop("data_json") or "{}")
        except Exception:
            d["data"] = {}
        out.append(d)
    return out

def get_latest_report(incident_id: int) -> Optional[Dict[str, Any]]:
    sql = """SELECT id, report_json, report_md, created_at
             FROM reports WHERE incident_id=? ORDER BY id DESC LIMIT 1"""
    with _conn(rowdict=True) as con:
        r = con.execute(sql, (incident_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    try:
        d["report"] = json.loads(d.pop("report_json") or "{}")
    except Exception:
        d["report"] = {}
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
