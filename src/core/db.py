import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = "runtime/cases.db"


def get_connection():
    Path("runtime").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT,
            client_id TEXT,
            module TEXT,
            status TEXT,
            severity TEXT,
            risk_score INTEGER,
            decision_code TEXT,
            payload TEXT,
            full_response TEXT,
            created_at TEXT
        )
    """)

    # indice corretto (fix definitivo errore precedente)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cases_created_at
        ON cases(created_at)
    """)

    conn.commit()
    conn.close()


def insert_case(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO cases (
            decision_id,
            client_id,
            module,
            status,
            severity,
            risk_score,
            decision_code,
            payload,
            full_response,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("decision_id"),
        data.get("client_id"),
        data.get("module"),
        data.get("status"),
        data.get("severity"),
        data.get("risk_score"),
        data.get("decision_code"),
        json.dumps(data.get("payload")),
        json.dumps(data.get("full_response")),
        datetime.now(timezone.utc).isoformat()
    ))

    conn.commit()
    conn.close()


def get_cases(limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, decision_id, client_id, module,
               status, severity, risk_score,
               decision_code, created_at
        FROM cases
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
