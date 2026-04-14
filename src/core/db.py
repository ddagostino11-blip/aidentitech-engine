import sqlite3
import json
import secrets
import hashlib
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = "runtime/cases.db"


def get_connection():
    Path("runtime").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _api_key_preview(api_key_hash: str) -> str:
    if not api_key_hash:
        return "hidden"
    return f"{api_key_hash[:8]}..."


def _looks_like_sha256(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value.lower())
    )


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # =========================
    # CASES TABLE
    # =========================
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

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cases_created_at
        ON cases(created_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cases_client_id
        ON cases(client_id)
    """)

    # =========================
    # API KEYS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT UNIQUE,
            client_id TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_keys_client_id
        ON api_keys(client_id)
    """)

    conn.commit()
    conn.close()


def insert_api_key(api_key: str, client_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    api_key_hash = _hash_api_key(api_key)

    cursor.execute("""
        INSERT OR IGNORE INTO api_keys (api_key, client_id, created_at)
        VALUES (?, ?, ?)
    """, (
        api_key_hash,
        client_id,
        datetime.now(timezone.utc).isoformat()
    ))

    conn.commit()
    conn.close()


def get_client_by_api_key(api_key: str):
    conn = get_connection()
    cursor = conn.cursor()

    api_key_hash = _hash_api_key(api_key)

    cursor.execute("""
        SELECT client_id
        FROM api_keys
        WHERE api_key = ?
        LIMIT 1
    """, (api_key_hash,))

    row = cursor.fetchone()
    conn.close()

    return row["client_id"] if row else None


def list_api_keys():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, api_key, client_id, created_at
        FROM api_keys
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "api_key_preview": _api_key_preview(row["api_key"]),
            "client_id": row["client_id"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def revoke_api_key(api_key: str):
    conn = get_connection()
    cursor = conn.cursor()

    api_key_hash = _hash_api_key(api_key)

    cursor.execute("""
        DELETE FROM api_keys
        WHERE api_key = ?
    """, (api_key_hash,))

    affected = cursor.rowcount
    conn.commit()
    conn.close()

    return affected > 0


def rotate_api_key(old_api_key: str):
    conn = get_connection()
    cursor = conn.cursor()

    old_api_key_hash = _hash_api_key(old_api_key)

    cursor.execute("""
        SELECT client_id
        FROM api_keys
        WHERE api_key = ?
        LIMIT 1
    """, (old_api_key_hash,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    client_id = row["client_id"]
    new_api_key = f"key_{secrets.token_hex(16)}"
    new_api_key_hash = _hash_api_key(new_api_key)

    cursor.execute("""
        DELETE FROM api_keys
        WHERE api_key = ?
    """, (old_api_key_hash,))

    cursor.execute("""
        INSERT INTO api_keys (api_key, client_id, created_at)
        VALUES (?, ?, ?)
    """, (
        new_api_key_hash,
        client_id,
        datetime.now(timezone.utc).isoformat()
    ))

    conn.commit()
    conn.close()

    return new_api_key


def migrate_plaintext_api_keys():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, api_key, client_id
        FROM api_keys
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    migrated = 0
    deleted_duplicates = 0

    for row in rows:
        key_id = row["id"]
        raw_value = row["api_key"]
        client_id = row["client_id"]

        if _looks_like_sha256(raw_value):
            continue

        hashed_value = _hash_api_key(raw_value)

        # Se esiste già un record con stesso hash e stesso client,
        # eliminiamo il legacy plaintext per evitare violazione UNIQUE.
        cursor.execute("""
            SELECT id
            FROM api_keys
            WHERE api_key = ?
              AND client_id = ?
              AND id != ?
            LIMIT 1
        """, (hashed_value, client_id, key_id))

        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                DELETE FROM api_keys
                WHERE id = ?
            """, (key_id,))
            deleted_duplicates += 1
            continue

        cursor.execute("""
            UPDATE api_keys
            SET api_key = ?
            WHERE id = ?
        """, (hashed_value, key_id))

        migrated += 1

    conn.commit()
    conn.close()

    return {
        "migrated": migrated,
        "deleted_duplicates": deleted_duplicates,
    }


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


def get_cases(client_id: str | None = None, status: str | None = None, limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, decision_id, client_id, module,
               status, severity, risk_score,
               decision_code, created_at
        FROM cases
    """

    conditions = []
    params = []

    if client_id:
        conditions.append("client_id = ?")
        params.append(client_id)

    if status:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_case_by_decision_id(decision_id: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT full_response
        FROM cases
        WHERE decision_id = ?
        LIMIT 1
    """, (decision_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return json.loads(row["full_response"])
