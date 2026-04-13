import json
import uuid
from datetime import datetime, timezone
from typing import Any

from src.core.db import get_connection


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _from_json(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)


def create_case(
    *,
    decision_id: str,
    client_id: str,
    module: str,
    payload: dict,
    response: dict,
) -> dict:
    case_id = str(uuid.uuid4())
    created_at = _now_utc_iso()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO cases (
                case_id,
                decision_id,
                client_id,
                module,
                status,
                severity,
                risk_score,
                decision_code,
                recommended_action,
                review_required,
                blocking_issues_count,
                regulatory_impact,
                batch_disposition,
                decision_timestamp,
                policy_profile,
                ledger_hash,
                payload_json,
                decision_json,
                issues_json,
                audit_json,
                explanation_json,
                primary_issue_json,
                versioning_json,
                compliance_scope_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                decision_id,
                client_id,
                module,
                response.get("status"),
                response.get("severity"),
                int(response.get("risk_score", 0)),
                response.get("decision_code"),
                response.get("recommended_action"),
                1 if response.get("review_required") else 0,
                int(response.get("blocking_issues_count", 0)),
                response.get("regulatory_impact"),
                response.get("batch_disposition"),
                response.get("decision_timestamp"),
                response.get("policy_profile"),
                response.get("ledger_hash"),
                _to_json(payload or {}),
                _to_json(response),
                _to_json(response.get("issues", [])),
                _to_json(response.get("audit", [])),
                _to_json(response.get("explanation", {})),
                _to_json(response.get("primary_issue")),
                _to_json(response.get("versioning", {})),
                _to_json(response.get("compliance_scope", {})),
                created_at,
            ),
        )

    return get_case(case_id)


def get_case(case_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "case_id": row["case_id"],
        "decision_id": row["decision_id"],
        "client_id": row["client_id"],
        "module": row["module"],
        "status": row["status"],
        "severity": row["severity"],
        "risk_score": row["risk_score"],
        "decision_code": row["decision_code"],
        "recommended_action": row["recommended_action"],
        "review_required": bool(row["review_required"]),
        "blocking_issues_count": row["blocking_issues_count"],
        "regulatory_impact": row["regulatory_impact"],
        "batch_disposition": row["batch_disposition"],
        "decision_timestamp": row["decision_timestamp"],
        "policy_profile": row["policy_profile"],
        "ledger_hash": row["ledger_hash"],
        "payload": _from_json(row["payload_json"]),
        "decision": _from_json(row["decision_json"]),
        "issues": _from_json(row["issues_json"]),
        "audit": _from_json(row["audit_json"]),
        "explanation": _from_json(row["explanation_json"]),
        "primary_issue": _from_json(row["primary_issue_json"]),
        "versioning": _from_json(row["versioning_json"]),
        "compliance_scope": _from_json(row["compliance_scope_json"]),
        "created_at": row["created_at"],
    }


def list_cases(
    *,
    client_id: str | None = None,
    module: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    query = """
        SELECT
            case_id,
            decision_id,
            client_id,
            module,
            status,
            severity,
            risk_score,
            decision_code,
            recommended_action,
            review_required,
            blocking_issues_count,
            regulatory_impact,
            batch_disposition,
            decision_timestamp,
            policy_profile,
            ledger_hash,
            created_at
        FROM cases
    """

    conditions = []
    params: list[Any] = []

    if client_id:
        conditions.append("client_id = ?")
        params.append(client_id)

    if module:
        conditions.append("module = ?")
        params.append(module)

    if status:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY decision_timestamp DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "case_id": row["case_id"],
            "decision_id": row["decision_id"],
            "client_id": row["client_id"],
            "module": row["module"],
            "status": row["status"],
            "severity": row["severity"],
            "risk_score": row["risk_score"],
            "decision_code": row["decision_code"],
            "recommended_action": row["recommended_action"],
            "review_required": bool(row["review_required"]),
            "blocking_issues_count": row["blocking_issues_count"],
            "regulatory_impact": row["regulatory_impact"],
            "batch_disposition": row["batch_disposition"],
            "decision_timestamp": row["decision_timestamp"],
            "policy_profile": row["policy_profile"],
            "ledger_hash": row["ledger_hash"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
