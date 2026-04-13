from fastapi import APIRouter, HTTPException, Query
from src.core.db import get_connection, get_case_by_decision_id

router = APIRouter()


@router.get("/cases")
def get_cases(
    client_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50),
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

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@router.get("/cases/{decision_id}")
def get_case_by_id(decision_id: str):
    case = get_case_by_decision_id(decision_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return case
