"""Conexão SQLite, schema do plantão e migrações versionadas (schema/*.sql)."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

from infrastructure.caminhos import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    chart_hash TEXT NOT NULL,
    cpf_hash TEXT NOT NULL,
    birth_year INTEGER,
    sex TEXT,
    allergies TEXT,
    diagnosis TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT,
    thread_id TEXT,
    severity TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    acked_at TEXT,
    closed_at TEXT,
    UNIQUE(thread_id, reason)
);
CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    hr INTEGER NOT NULL,
    sbp INTEGER NOT NULL,
    dbp INTEGER NOT NULL,
    spo2 INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    drug TEXT NOT NULL,
    dose_mg REAL NOT NULL,
    route TEXT NOT NULL,
    action TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS movement_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    posture TEXT NOT NULL,
    zone TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS modality_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    body_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _apply_versioned_sql(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    schema_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema")
    if not os.path.isdir(schema_dir):
        return
    for name in sorted(os.listdir(schema_dir)):
        if not name.endswith(".sql") or name.endswith("_down.sql"):
            continue
        version = name[: -len(".sql")]
        found = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE id = ?",
            (version,),
        ).fetchone()
        if found:
            continue
        with open(os.path.join(schema_dir, name), encoding="utf-8") as handle:
            conn.executescript(handle.read())
        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, ?)",
            (version, utcnow()),
        )


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(alerts)").fetchall()}
    if "acked_at" not in cols:
        conn.execute("ALTER TABLE alerts ADD COLUMN acked_at TEXT")
    if "closed_at" not in cols:
        conn.execute("ALTER TABLE alerts ADD COLUMN closed_at TEXT")
    _apply_versioned_sql(conn)
    conn.commit()


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_patient(conn: sqlite3.Connection, patient_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    return dict(row) if row else None


def list_patients(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM patients ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def emit_alert(
    conn: sqlite3.Connection,
    *,
    patient_id: str,
    thread_id: str,
    severity: str,
    reason: str,
    source: str,
) -> bool:
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO alerts
            (patient_id, thread_id, severity, reason, source, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'open', ?)
        """,
        (patient_id, thread_id, severity, reason, source, utcnow()),
    )
    conn.commit()
    return cur.rowcount == 1


def list_alerts(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    if status:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE status = ? ORDER BY id DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def open_alert_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM alerts WHERE status = 'open'").fetchone()
    return int(row["n"])


def get_alert(conn: sqlite3.Connection, alert_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    return dict(row) if row else None


def ack_alert(conn: sqlite3.Connection, alert_id: int) -> dict | None:
    row = get_alert(conn, alert_id)
    if row is None or row["status"] == "closed":
        return row
    if row["status"] == "acked":
        return row
    conn.execute(
        "UPDATE alerts SET status = 'acked', acked_at = ? WHERE id = ?",
        (utcnow(), alert_id),
    )
    conn.commit()
    return get_alert(conn, alert_id)


def close_alert(conn: sqlite3.Connection, alert_id: int) -> dict | None:
    row = get_alert(conn, alert_id)
    if row is None:
        return None
    stamp = utcnow()
    acked = row["acked_at"] or stamp
    conn.execute(
        """
        UPDATE alerts
           SET status = 'closed',
               acked_at = COALESCE(acked_at, ?),
               closed_at = ?
         WHERE id = ?
        """,
        (acked, stamp, alert_id),
    )
    conn.commit()
    return get_alert(conn, alert_id)


def modality_report_kinds(conn, patient_id: str) -> set[str]:
    rows = conn.execute(
        "SELECT DISTINCT kind FROM modality_reports WHERE patient_id = ?",
        (patient_id,),
    ).fetchall()
    return {row["kind"] for row in rows}


def insert_vital(conn, patient_id, recorded_at, hr, sbp, dbp, spo2) -> None:
    conn.execute(
        "INSERT INTO vitals (patient_id, recorded_at, hr, sbp, dbp, spo2) VALUES (?, ?, ?, ?, ?, ?)",
        (patient_id, recorded_at, int(hr), int(sbp), int(dbp), int(spo2)),
    )


def list_vitals(conn, patient_id) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM vitals WHERE patient_id = ? ORDER BY recorded_at, id",
        (patient_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def insert_prescription(conn, patient_id, recorded_at, drug, dose_mg, route, action) -> None:
    conn.execute(
        """
        INSERT INTO prescriptions (patient_id, recorded_at, drug, dose_mg, route, action)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (patient_id, recorded_at, drug, float(dose_mg), route, action),
    )


def list_prescriptions(conn, patient_id) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY recorded_at, id",
        (patient_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def insert_movement(conn, patient_id, recorded_at, posture, zone) -> None:
    conn.execute(
        "INSERT INTO movement_events (patient_id, recorded_at, posture, zone) VALUES (?, ?, ?, ?)",
        (patient_id, recorded_at, posture, zone),
    )


def list_movement(conn, patient_id) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM movement_events WHERE patient_id = ? ORDER BY recorded_at, id",
        (patient_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_modality_report(conn, patient_id, kind, body: dict) -> None:
    conn.execute(
        """
        INSERT INTO modality_reports (patient_id, kind, body_json, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (patient_id, kind, json.dumps(body, ensure_ascii=False), utcnow()),
    )
    conn.commit()
