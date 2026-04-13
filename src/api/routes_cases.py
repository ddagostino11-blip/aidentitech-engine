from fastapi import APIRouter
from src.core.db import get_connection

router = APIRouter()


@router.get("/cases")
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
