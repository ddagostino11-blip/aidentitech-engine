import os
import sqlite3
import json
import secrets
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json

from src.core.ledger_chain import get_ledger_entries_by_decision_id


SQLITE_DB_PATH = "runtime/cases.db"
DATABASE_URL = os.getenv("DATABASE_URL")

CANONICAL_EVENT_TYPES = {"ENGINE_DECISION", "HUMAN_REVIEW", "ADMIN_OVERRIDE"}
ENGINE_EVENT_TYPES = {"ENGINE_DECISION", "LEGACY_ENGINE_DECISION", "LEGACY_UNKNOWN"}
REVIEW_EVENT_TYPES = {"HUMAN_REVIEW"}
OVERRIDE_EVENT_TYPES = {"ADMIN_OVERRIDE"}
STATE_CHANGE_EVENT_TYPES = REVIEW_EVENT_TYPES | OVERRIDE_EVENT_TYPES


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_postgres() -> bool:
    return bool(DATABASE_URL and DATABASE_URL.startswith("postgresql"))


def get_connection():
    if _is_postgres():
        return psycopg2.connect(DATABASE_URL)

    Path("runtime").mkdir(exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _fetchall_dicts(cursor):
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def _fetchone_dict(cursor):
    row = cursor.fetchone()

    if not row:
        return None

    return dict(row)


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


def _column_exists_sqlite(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col["name"] == column_name for col in columns)


def _column_exists_postgres(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name = %s
        LIMIT 1
    """, (table_name, column_name))
    return cursor.fetchone() is not None


def _parse_ts(ts: str | None):
    if not ts:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def init_db():
    conn = get_connection()

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id SERIAL PRIMARY KEY,
                decision_id TEXT UNIQUE,
                client_id TEXT,
                module TEXT,
                status TEXT,
                severity TEXT,
                risk_score INTEGER,
                decision_code TEXT,
                payload JSONB,
                full_response JSONB,
                dossier_hash TEXT,
                signature TEXT,
                created_at TIMESTAMPTZ
            )
        """)

        if not _column_exists_postgres(cursor, "cases", "dossier_hash"):
            cursor.execute("""
                ALTER TABLE cases
                ADD COLUMN dossier_hash TEXT
            """)

        if not _column_exists_postgres(cursor, "cases", "signature"):
            cursor.execute("""
                ALTER TABLE cases
                ADD COLUMN signature TEXT
            """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cases_created_at
            ON cases(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cases_client_id
            ON cases(client_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cases_dossier_hash
            ON cases(dossier_hash)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id SERIAL PRIMARY KEY,
                api_key TEXT UNIQUE,
                client_id TEXT,
                role TEXT DEFAULT 'client',
                created_at TIMESTAMPTZ
            )
        """)

        if not _column_exists_postgres(cursor, "api_keys", "role"):
            cursor.execute("""
                ALTER TABLE api_keys
                ADD COLUMN role TEXT DEFAULT 'client'
            """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_client_id
            ON api_keys(client_id)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_actions (
                id SERIAL PRIMARY KEY,
                decision_id TEXT,
                client_id TEXT,
                reviewer_id TEXT,
                action TEXT,
                reason TEXT,
                ledger_hash TEXT,
                actor_role TEXT,
                ledger_event_id TEXT,
                created_at TIMESTAMPTZ
            )
        """)

        if not _column_exists_postgres(cursor, "review_actions", "ledger_hash"):
            cursor.execute("""
                ALTER TABLE review_actions
                ADD COLUMN ledger_hash TEXT
            """)

        if not _column_exists_postgres(cursor, "review_actions", "actor_role"):
            cursor.execute("""
                ALTER TABLE review_actions
                ADD COLUMN actor_role TEXT
            """)

        if not _column_exists_postgres(cursor, "review_actions", "ledger_event_id"):
            cursor.execute("""
                ALTER TABLE review_actions
                ADD COLUMN ledger_event_id TEXT
            """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_review_actions_decision_id
            ON review_actions(decision_id)
        """)

        conn.commit()
        conn.close()
        return

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

    if not _column_exists_sqlite(cursor, "cases", "dossier_hash"):
        cursor.execute("""
            ALTER TABLE cases
            ADD COLUMN dossier_hash TEXT
        """)

    if not _column_exists_sqlite(cursor, "cases", "signature"):
        cursor.execute("""
            ALTER TABLE cases
            ADD COLUMN signature TEXT
        """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cases_created_at
        ON cases(created_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cases_client_id
        ON cases(client_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cases_dossier_hash
        ON cases(dossier_hash)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT UNIQUE,
            client_id TEXT,
            role TEXT DEFAULT 'client',
            created_at TEXT
        )
    """)

    if not _column_exists_sqlite(cursor, "api_keys", "role"):
        cursor.execute("""
            ALTER TABLE api_keys
            ADD COLUMN role TEXT DEFAULT 'client'
        """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_keys_client_id
        ON api_keys(client_id)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT,
            client_id TEXT,
            reviewer_id TEXT,
            action TEXT,
            reason TEXT,
            ledger_hash TEXT,
            actor_role TEXT,
            ledger_event_id TEXT,
            created_at TEXT
        )
    """)

    if not _column_exists_sqlite(cursor, "review_actions", "ledger_hash"):
        cursor.execute("""
            ALTER TABLE review_actions
            ADD COLUMN ledger_hash TEXT
        """)

    if not _column_exists_sqlite(cursor, "review_actions", "actor_role"):
        cursor.execute("""
            ALTER TABLE review_actions
            ADD COLUMN actor_role TEXT
        """)

    if not _column_exists_sqlite(cursor, "review_actions", "ledger_event_id"):
        cursor.execute("""
            ALTER TABLE review_actions
            ADD COLUMN ledger_event_id TEXT
        """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_review_actions_decision_id
        ON review_actions(decision_id)
    """)

    conn.commit()
    conn.close()


def insert_api_key(api_key: str, client_id: str, role: str = "client"):
    conn = get_connection()
    api_key_hash = _hash_api_key(api_key)
    created_at = _utc_now_iso()

    if _is_postgres():
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO api_keys (api_key, client_id, role, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (api_key) DO NOTHING
        """, (api_key_hash, client_id, role, created_at))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO api_keys (api_key, client_id, role, created_at)
            VALUES (?, ?, ?, ?)
        """, (api_key_hash, client_id, role, created_at))

    conn.commit()
    conn.close()


def get_client_by_api_key(api_key: str):
    conn = get_connection()

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT client_id, role
            FROM api_keys
            WHERE api_key = %s
            LIMIT 1
        """, (_hash_api_key(api_key),))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT client_id, role
            FROM api_keys
            WHERE api_key = ?
            LIMIT 1
        """, (_hash_api_key(api_key),))

    row = _fetchone_dict(cursor)
    conn.close()

    if not row:
        return None

    return {
        "client_id": row["client_id"],
        "role": row.get("role") or "client",
    }


def list_api_keys():
    conn = get_connection()

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor()

    cursor.execute("""
        SELECT id, api_key, client_id, role, created_at
        FROM api_keys
        ORDER BY id DESC
    """)

    rows = _fetchall_dicts(cursor)
    conn.close()

    return [
        {
            "id": row["id"],
            "api_key_preview": _api_key_preview(row["api_key"]),
            "client_id": row["client_id"],
            "role": row.get("role") or "client",
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def revoke_api_key(api_key: str):
    conn = get_connection()
    api_key_hash = _hash_api_key(api_key)

    if _is_postgres():
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM api_keys
            WHERE api_key = %s
        """, (api_key_hash,))
    else:
        cursor = conn.cursor()
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
    old_api_key_hash = _hash_api_key(old_api_key)

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT client_id, role
            FROM api_keys
            WHERE api_key = %s
            LIMIT 1
        """, (old_api_key_hash,))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT client_id, role
            FROM api_keys
            WHERE api_key = ?
            LIMIT 1
        """, (old_api_key_hash,))

    row = _fetchone_dict(cursor)

    if not row:
        conn.close()
        return None

    client_id = row["client_id"]
    role = row.get("role") or "client"
    new_api_key = f"key_{secrets.token_hex(16)}"
    new_api_key_hash = _hash_api_key(new_api_key)
    created_at = _utc_now_iso()

    if _is_postgres():
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM api_keys
            WHERE api_key = %s
        """, (old_api_key_hash,))
        cursor.execute("""
            INSERT INTO api_keys (api_key, client_id, role, created_at)
            VALUES (%s, %s, %s, %s)
        """, (new_api_key_hash, client_id, role, created_at))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM api_keys
            WHERE api_key = ?
        """, (old_api_key_hash,))
        cursor.execute("""
            INSERT INTO api_keys (api_key, client_id, role, created_at)
            VALUES (?, ?, ?, ?)
        """, (new_api_key_hash, client_id, role, created_at))

    conn.commit()
    conn.close()

    return new_api_key


def migrate_plaintext_api_keys():
    if _is_postgres():
        return {"migrated": 0, "deleted_duplicates": 0}

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
    created_at = _utc_now_iso()

    if _is_postgres():
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
                dossier_hash,
                signature,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get("decision_id"),
            data.get("client_id"),
            data.get("module"),
            data.get("status"),
            data.get("severity"),
            data.get("risk_score"),
            data.get("decision_code"),
            Json(data.get("payload")),
            Json(data.get("full_response")),
            data.get("dossier_hash"),
            data.get("signature"),
            created_at,
        ))
    else:
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
                dossier_hash,
                signature,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get("dossier_hash"),
            data.get("signature"),
            created_at,
        ))

    conn.commit()
    conn.close()


def get_cases(client_id: str | None = None, status: str | None = None, limit: int = 50):
    conn = get_connection()

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = """
            SELECT id, decision_id, client_id, module,
                   status, severity, risk_score,
                   decision_code, dossier_hash, signature, created_at
            FROM cases
        """
        conditions = []
        params = []

        if client_id:
            conditions.append("client_id = %s")
            params.append(client_id)

        if status:
            conditions.append("status = %s")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT %s"
        params.append(limit)
        cursor.execute(query, tuple(params))
    else:
        cursor = conn.cursor()
        query = """
            SELECT id, decision_id, client_id, module,
                   status, severity, risk_score,
                   decision_code, dossier_hash, signature, created_at
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

    rows = _fetchall_dicts(cursor)
    conn.close()

    for row in rows:
        row["created_at"] = str(row["created_at"])

    return rows


def get_case_by_decision_id(decision_id: str):
    conn = get_connection()

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT full_response, dossier_hash, signature
            FROM cases
            WHERE decision_id = %s
            LIMIT 1
        """, (decision_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT full_response, dossier_hash, signature
            FROM cases
            WHERE decision_id = ?
            LIMIT 1
        """, (decision_id,))

    row = _fetchone_dict(cursor)
    conn.close()

    if not row:
        return None

    case = row["full_response"] if _is_postgres() else json.loads(row["full_response"])
    case["dossier_hash"] = row["dossier_hash"]
    case["signature"] = row.get("signature")
    return case


def get_latest_review_by_decision_id(decision_id: str):
    conn = get_connection()

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id, decision_id, client_id, reviewer_id,
                   action, reason, ledger_hash, actor_role, ledger_event_id, created_at
            FROM review_actions
            WHERE decision_id = %s
            ORDER BY id DESC
            LIMIT 1
        """, (decision_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, decision_id, client_id, reviewer_id,
                   action, reason, ledger_hash, actor_role, ledger_event_id, created_at
            FROM review_actions
            WHERE decision_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (decision_id,))

    row = _fetchone_dict(cursor)
    conn.close()

    if not row:
        return None

    row["created_at"] = str(row["created_at"])
    return row


def _build_case_summary(row: dict) -> dict:
    if _is_postgres():
        full_response = row["full_response"]
    else:
        full_response = json.loads(row["full_response"])

    latest_review = get_latest_review_by_decision_id(full_response.get("decision_id"))

    engine_status = full_response.get("status")
    final_status = latest_review["action"] if latest_review else engine_status

    if latest_review:
        actor_role = latest_review.get("actor_role")
        review_state = "OVERRIDDEN" if actor_role == "super_admin" else "REVIEWED"
    else:
        review_state = "PENDING"

    return {
        "id": row["id"],
        "decision_id": full_response.get("decision_id"),
        "client_id": full_response.get("client_id"),
        "module": full_response.get("module"),
        "status": final_status,
        "engine_status": engine_status,
        "final_status": final_status,
        "review_state": review_state,
        "severity": full_response.get("severity"),
        "risk_score": full_response.get("risk_score"),
        "decision_code": full_response.get("decision_code"),
        "dossier_hash": row.get("dossier_hash"),
        "signature": row.get("signature"),
        "created_at": str(row["created_at"]),
    }


def get_case_summaries(
    client_id: str,
    status: str | None = None,
    severity: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
):
    conn = get_connection()

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        placeholder = "%s"
    else:
        cursor = conn.cursor()
        placeholder = "?"

    query = f"""
        SELECT id, full_response, dossier_hash, signature, created_at
        FROM cases
        WHERE client_id = {placeholder}
    """
    params = [client_id]

    if date_from:
        query += f" AND created_at >= {placeholder}"
        params.append(date_from)

    if date_to:
        query += f" AND created_at <= {placeholder}"
        params.append(date_to)

    query += f" ORDER BY id DESC LIMIT {placeholder}"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = _fetchall_dicts(cursor)
    conn.close()

    summaries = [_build_case_summary(row) for row in rows]

    if status:
        summaries = [row for row in summaries if row["status"] == status]

    if severity:
        summaries = [row for row in summaries if row["severity"] == severity]

    return summaries


def insert_review_action(
    decision_id: str,
    client_id: str,
    reviewer_id: str,
    action: str,
    reason: str | None = None,
    ledger_hash: str | None = None,
    actor_role: str | None = None,
    ledger_event_id: str | None = None,
):
    conn = get_connection()
    created_at = _utc_now_iso()

    if _is_postgres():
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO review_actions (
                decision_id,
                client_id,
                reviewer_id,
                action,
                reason,
                ledger_hash,
                actor_role,
                ledger_event_id,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            decision_id,
            client_id,
            reviewer_id,
            action,
            reason,
            ledger_hash,
            actor_role,
            ledger_event_id,
            created_at,
        ))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO review_actions (
                decision_id,
                client_id,
                reviewer_id,
                action,
                reason,
                ledger_hash,
                actor_role,
                ledger_event_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id,
            client_id,
            reviewer_id,
            action,
            reason,
            ledger_hash,
            actor_role,
            ledger_event_id,
            created_at,
        ))

    conn.commit()
    conn.close()


def get_reviews_by_decision_id(decision_id: str):
    conn = get_connection()

    if _is_postgres():
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id, decision_id, client_id, reviewer_id,
                   action, reason, ledger_hash, actor_role, ledger_event_id, created_at
            FROM review_actions
            WHERE decision_id = %s
            ORDER BY id DESC
        """, (decision_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, decision_id, client_id, reviewer_id,
                   action, reason, ledger_hash, actor_role, ledger_event_id, created_at
            FROM review_actions
            WHERE decision_id = ?
            ORDER BY id DESC
        """, (decision_id,))

    rows = _fetchall_dicts(cursor)
    conn.close()

    for row in rows:
        row["created_at"] = str(row["created_at"])

    return rows


def get_case_timeline(decision_id: str):
    case = get_case_by_decision_id(decision_id)
    reviews = get_reviews_by_decision_id(decision_id)

    if not case:
        return None

    timeline = []

    timeline.append({
        "type": "DECISION",
        "timestamp": case.get("decision_timestamp"),
        "data": {
            "status": case.get("status"),
            "severity": case.get("severity"),
            "risk_score": case.get("risk_score"),
            "decision_code": case.get("decision_code"),
            "ledger_hash": case.get("ledger_hash"),
        }
    })

    for review in reviews:
        actor_role = review.get("actor_role")
        event_type = "OVERRIDE" if actor_role == "super_admin" else "REVIEW"

        event_data = {
            "action": review.get("action"),
            "reason": review.get("reason"),
            "reviewer_id": review.get("reviewer_id"),
            "ledger_hash": review.get("ledger_hash"),
            "actor_role": actor_role,
            "ledger_event_id": review.get("ledger_event_id"),
        }

        timeline.append({
            "type": event_type,
            "timestamp": review.get("created_at"),
            "data": event_data,
        })

    timeline = sorted(
        timeline,
        key=lambda item: _parse_ts(item.get("timestamp"))
    )

    return {
        "decision_id": decision_id,
        "timeline": timeline,
        "reviews_count": len(reviews),
    }


def _base_normalized_ledger_entry(entry: dict) -> dict:
    data = entry.get("data", {})
    metadata = data.get("metadata") or {}

    return {
        "event_id": entry.get("event_id"),
        "timestamp": entry.get("timestamp"),
        "event_type": None,
        "decision_id": data.get("decision_id"),
        "client_id": data.get("client_id"),
        "module": data.get("module"),
        "status": None,
        "severity": None,
        "risk_score": None,
        "decision_code": None,
        "review_action": None,
        "reviewer_id": None,
        "reason": None,
        "ledger_hash": entry.get("hash"),
        "source_format": "unknown",
        "raw_event_type": data.get("event_type"),
        "override_type": metadata.get("override_type"),
        "previous_status": metadata.get("previous_status"),
        "actor_role": metadata.get("actor_role"),
    }


def _normalize_ledger_entry(entry: dict) -> dict | None:
    data = entry.get("data", {})
    event_type = data.get("event_type")

    normalized = _base_normalized_ledger_entry(entry)

    if event_type == "ENGINE_DECISION":
        normalized.update({
            "event_type": "ENGINE_DECISION",
            "status": data.get("status"),
            "severity": data.get("severity"),
            "risk_score": data.get("risk_score"),
            "decision_code": data.get("decision_code"),
            "source_format": "canonical",
        })
        return normalized

    if event_type == "HUMAN_REVIEW":
        normalized.update({
            "event_type": "HUMAN_REVIEW",
            "status": data.get("review_action") or data.get("status"),
            "review_action": data.get("review_action"),
            "reviewer_id": data.get("reviewer_id"),
            "reason": data.get("reason"),
            "source_format": "canonical",
        })
        return normalized

    if event_type == "ADMIN_OVERRIDE":
        normalized.update({
            "event_type": "ADMIN_OVERRIDE",
            "status": data.get("review_action") or data.get("status"),
            "review_action": data.get("review_action"),
            "reviewer_id": data.get("reviewer_id"),
            "reason": data.get("reason"),
            "source_format": "canonical",
        })
        return normalized

    decision = data.get("decision")

    if isinstance(decision, dict):
        normalized.update({
            "event_type": "LEGACY_ENGINE_DECISION",
            "status": decision.get("status"),
            "severity": decision.get("severity"),
            "risk_score": decision.get("risk_score"),
            "decision_code": decision.get("decision_code"),
            "source_format": "legacy_dict",
        })
        return normalized

    if isinstance(decision, str):
        normalized.update({
            "event_type": "LEGACY_ENGINE_DECISION",
            "status": decision,
            "source_format": "legacy_string",
        })
        return normalized

    if any(
        key in data
        for key in ["client_id", "module", "decision_id", "status", "severity", "risk_score"]
    ):
        normalized.update({
            "event_type": "LEGACY_UNKNOWN",
            "status": data.get("status"),
            "severity": data.get("severity"),
            "risk_score": data.get("risk_score"),
            "decision_code": data.get("decision_code"),
            "source_format": "legacy_unknown",
        })
        return normalized

    return None


def _build_timeline_event_from_normalized_entry(normalized: dict) -> dict | None:
    event_type = normalized.get("event_type")

    if event_type in REVIEW_EVENT_TYPES:
        return {
            "type": "REVIEW",
            "timestamp": normalized.get("timestamp"),
            "data": {
                "action": normalized.get("review_action"),
                "reason": normalized.get("reason"),
                "reviewer_id": normalized.get("reviewer_id"),
                "ledger_hash": normalized.get("ledger_hash"),
                "source_format": normalized.get("source_format"),
                "actor_role": normalized.get("actor_role"),
                "ledger_event_id": normalized.get("event_id"),
            }
        }

    if event_type in OVERRIDE_EVENT_TYPES:
        return {
            "type": "OVERRIDE",
            "timestamp": normalized.get("timestamp"),
            "data": {
                "action": normalized.get("review_action"),
                "reason": normalized.get("reason"),
                "reviewer_id": normalized.get("reviewer_id"),
                "ledger_hash": normalized.get("ledger_hash"),
                "source_format": normalized.get("source_format"),
                "override_type": normalized.get("override_type"),
                "previous_status": normalized.get("previous_status"),
                "actor_role": normalized.get("actor_role"),
                "ledger_event_id": normalized.get("event_id"),
            }
        }

    if event_type in ENGINE_EVENT_TYPES:
        return {
            "type": "DECISION",
            "timestamp": normalized.get("timestamp"),
            "data": {
                "status": normalized.get("status"),
                "severity": normalized.get("severity"),
                "risk_score": normalized.get("risk_score"),
                "decision_code": normalized.get("decision_code"),
                "ledger_hash": normalized.get("ledger_hash"),
                "source_format": normalized.get("source_format"),
                "ledger_event_id": normalized.get("event_id"),
            }
        }

    return None


def get_case_timeline_from_ledger(decision_id: str):
    entries = get_ledger_entries_by_decision_id(decision_id)

    if not entries:
        return None

    timeline = []

    for entry in entries:
        normalized = _normalize_ledger_entry(entry)
        if not normalized:
            continue

        event = _build_timeline_event_from_normalized_entry(normalized)
        if event:
            timeline.append(event)

    timeline = sorted(
        timeline,
        key=lambda item: _parse_ts(item.get("timestamp"))
    )

    return {
        "decision_id": decision_id,
        "timeline": timeline,
        "events_count": len(timeline),
    }
