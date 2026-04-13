from fastapi import APIRouter, HTTPException, Query
from src.core.db import get_connection, get_case_by_decision_id

router = APIRouter(tags=["cases"])


# =========================
# 1️⃣ STATS (SEMPRE PRIMA)
# =========================
@router.get("/cases/stats")
def get_cases_stats(
    client_id: str | None = Query(default=None),
):
    conn = get_connection()
    cursor = conn.cursor()

    base_query = "FROM cases"
    conditions = []
    params = []

    # filtro opzionale per client
    if client_id:
        conditions.append("client_id = ?")
        params.append(client_id)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    # aggregazione per status
    cursor.execute(
        f"SELECT status, COUNT(*) as count {base_query} GROUP BY status",
        tuple(params),
    )
    status_rows = cursor.fetchall()

    # aggregazione per severity
    cursor.execute(
        f"SELECT severity, COUNT(*) as count {base_query} GROUP BY severity",
        tuple(params),
    )
    severity_rows = cursor.fetchall()

    # totale
    cursor.execute(
        f"SELECT COUNT(*) as total {base_query}",
        tuple(params),
    )
    total_row = cursor.fetchone()

    conn.close()

    return {
        "total_cases": total_row["total"] if total_row else 0,
        "by_status": {row["status"]: row["count"] for row in status_rows},
        "by_severity": {row["severity"]: row["count"] for row in severity_rows},
    }


# =========================
# 2️⃣ LISTA CASI
# =========================
@router.get("/cases")
def get_cases(
    client_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
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

    if severity:
        conditions.append("severity = ?")
        params.append(severity)

    if date_from:
        conditions.append("created_at >= ?")
        params.append(date_from)

    if date_to:
        conditions.append("created_at <= ?")
        params.append(date_to)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# =========================
# 3️⃣ SINGOLO CASE (SEMPRE ULTIMO)
# =========================
@router.get("/cases/{decision_id}")
def get_case_by_id(decision_id: str):
    case = get_case_by_decision_id(decision_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return case
