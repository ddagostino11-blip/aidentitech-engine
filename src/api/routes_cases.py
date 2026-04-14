from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import StreamingResponse
from src.core.db import get_connection, get_case_by_decision_id
from src.core.auth import get_client_from_api_key
from src.core.pdf_generator import generate_dossier_pdf
from src.core.dossier_seal import build_dossier_payload, compute_dossier_hash
import csv
import io

router = APIRouter(tags=["cases"])


def _client_from_key(x_api_key: str | None) -> str:
    try:
        return get_client_from_api_key(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _load_authorized_case(decision_id: str, x_api_key: str | None):
    client_id = _client_from_key(x_api_key)

    case = get_case_by_decision_id(decision_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if case.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return case


# =========================
# 1️⃣ STATS
# =========================
@router.get("/cases/stats")
def get_cases_stats(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    client_id = _client_from_key(x_api_key)

    conn = get_connection()
    cursor = conn.cursor()

    base_query = "FROM cases WHERE client_id = ?"
    params = [client_id]

    cursor.execute(
        f"SELECT status, COUNT(*) as count {base_query} GROUP BY status",
        tuple(params),
    )
    status_rows = cursor.fetchall()

    cursor.execute(
        f"SELECT severity, COUNT(*) as count {base_query} GROUP BY severity",
        tuple(params),
    )
    severity_rows = cursor.fetchall()

    cursor.execute(
        f"SELECT COUNT(*) as total {base_query}",
        tuple(params),
    )
    total_row = cursor.fetchone()

    conn.close()

    return {
        "client_id": client_id,
        "total_cases": total_row["total"] if total_row else 0,
        "by_status": {row["status"]: row["count"] for row in status_rows},
        "by_severity": {row["severity"]: row["count"] for row in severity_rows},
    }


# =========================
# 2️⃣ EXPORT CSV
# =========================
@router.get("/cases/export")
def export_cases(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    client_id = _client_from_key(x_api_key)

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT decision_id, client_id, module,
               status, severity, risk_score,
               decision_code, created_at
        FROM cases
    """

    conditions = ["client_id = ?"]
    params = [client_id]

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

    query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "decision_id",
        "client_id",
        "module",
        "status",
        "severity",
        "risk_score",
        "decision_code",
        "created_at",
    ])

    for row in rows:
        writer.writerow([
            row["decision_id"],
            row["client_id"],
            row["module"],
            row["status"],
            row["severity"],
            row["risk_score"],
            row["decision_code"],
            row["created_at"],
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cases_export.csv"},
    )


# =========================
# 3️⃣ LISTA CASI
# =========================
@router.get("/cases")
def get_cases(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    client_id = _client_from_key(x_api_key)

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, decision_id, client_id, module,
               status, severity, risk_score,
               decision_code, created_at
        FROM cases
    """

    conditions = ["client_id = ?"]
    params = [client_id]

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

    query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# =========================
# 4️⃣ DOSSIER CASE
# =========================
@router.get("/cases/{decision_id}/dossier")
def get_case_dossier(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case = _load_authorized_case(decision_id, x_api_key)

    dossier = build_dossier_payload(case)
    dossier_hash = compute_dossier_hash(dossier)

    return {
        **dossier,
        "dossier_hash": dossier_hash,
    }


# =========================
# 5️⃣ VERIFY DOSSIER
# =========================
@router.get("/cases/{decision_id}/verify")
def verify_case_dossier(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case = _load_authorized_case(decision_id, x_api_key)

    dossier = build_dossier_payload(case)
    dossier_hash = compute_dossier_hash(dossier)

    return {
        "decision_id": case.get("decision_id"),
        "client_id": case.get("client_id"),
        "module": case.get("module"),
        "verified": True,
        "dossier_hash": dossier_hash,
        "ledger_hash": case.get("ledger_hash"),
    }


# =========================
# 6️⃣ DOSSIER PDF
# =========================
@router.get("/cases/{decision_id}/dossier/pdf")
def get_case_dossier_pdf(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case = _load_authorized_case(decision_id, x_api_key)

    dossier = build_dossier_payload(case)
    dossier_hash = compute_dossier_hash(dossier)

    pdf_payload = {
        **dossier,
        "dossier_hash": dossier_hash,
    }

    pdf_buffer = generate_dossier_pdf(pdf_payload)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=dossier_{decision_id}.pdf"
        },
    )


# =========================
# 7️⃣ SINGOLO CASE
# =========================
@router.get("/cases/{decision_id}")
def get_case_by_id(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case = _load_authorized_case(decision_id, x_api_key)
    return case
