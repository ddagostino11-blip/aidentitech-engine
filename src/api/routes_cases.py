from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.ledger_chain import append_ledger_entry, build_canonical_ledger_data
from src.core.db import (
    get_case_by_decision_id,
    get_case_summaries,
    insert_review_action,
    get_reviews_by_decision_id,
    get_case_timeline,
    get_case_timeline_from_ledger,
)
from src.core.auth import get_client_from_api_key
from src.core.pdf_generator import generate_dossier_pdf
from src.core.dossier_seal import build_dossier_payload, compute_dossier_hash
import csv
import io

router = APIRouter(tags=["cases"])


class ReviewRequest(BaseModel):
    action: Literal["APPROVED", "REJECTED"]
    reason: str | None = None


class AdminOverrideRequest(BaseModel):
    action: Literal["APPROVED", "REJECTED"]
    reason: str
    override_type: Literal["BUG", "AUDIT", "MANUAL", "LEGAL", "DATA_FIX"]


def _auth_from_key(x_api_key: str | None) -> dict:
    try:
        return get_client_from_api_key(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _is_super_admin(auth: dict) -> bool:
    return auth.get("role") == "super_admin"


def _client_id_from_key(x_api_key: str | None) -> str:
    auth = _auth_from_key(x_api_key)
    return auth["client_id"]


def _require_reviewer(auth: dict):
    if auth.get("role") != "reviewer":
        raise HTTPException(status_code=403, detail="Reviewer access required")


def _require_super_admin(auth: dict):
    if auth.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")


def _load_authorized_case(decision_id: str, x_api_key: str | None):
    auth = _auth_from_key(x_api_key)
    client_id = auth["client_id"]

    case = get_case_by_decision_id(decision_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not _is_super_admin(auth) and case.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return case, auth


def _build_case_summary_response(case: dict, timeline: dict | None) -> dict:
    timeline_items = (timeline or {}).get("timeline", [])

    decision_events = [
        item for item in timeline_items
        if item.get("type") == "DECISION"
    ]
    state_change_events = [
        item for item in timeline_items
        if item.get("type") in {"REVIEW", "OVERRIDE"}
    ]

    latest_decision = decision_events[-1] if decision_events else None
    latest_state_change = state_change_events[-1] if state_change_events else None
    latest_event = timeline_items[-1] if timeline_items else None

    engine_status = (
        latest_decision.get("data", {}).get("status")
        if latest_decision
        else case.get("status")
    )
    latest_review_action = (
        latest_state_change.get("data", {}).get("action")
        if latest_state_change
        else None
    )
    final_status = latest_review_action or engine_status

    latest_ledger_hash = None
    if latest_event:
        latest_ledger_hash = latest_event.get("data", {}).get("ledger_hash")
    if not latest_ledger_hash:
        latest_ledger_hash = case.get("ledger_hash")

    return {
        "decision_id": case.get("decision_id"),
        "client_id": case.get("client_id"),
        "module": case.get("module"),
        "engine_status": engine_status,
        "final_status": final_status,
        "has_human_review": any(item.get("type") == "REVIEW" for item in state_change_events),
        "has_admin_override": any(item.get("type") == "OVERRIDE" for item in state_change_events),
        "latest_review_action": latest_review_action,
        "review_count": len([item for item in state_change_events if item.get("type") == "REVIEW"]),
        "override_count": len([item for item in state_change_events if item.get("type") == "OVERRIDE"]),
        "decision_timestamp": case.get("decision_timestamp"),
        "latest_event_timestamp": latest_event.get("timestamp") if latest_event else case.get("decision_timestamp"),
        "events_count": len(timeline_items),
        "latest_ledger_hash": latest_ledger_hash,
        "severity": case.get("severity"),
        "risk_score": case.get("risk_score"),
        "decision_code": case.get("decision_code"),
        "review_required": case.get("review_required"),
        "dossier_hash": case.get("dossier_hash"),
    }


# =========================
# 1️⃣ STATS
# =========================
@router.get("/cases/stats")
def get_cases_stats(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    client_id = _client_id_from_key(x_api_key)

    summaries = get_case_summaries(
        client_id=client_id,
        limit=10000,
    )

    by_status = {}
    by_severity = {}

    for row in summaries:
        status = row.get("status")
        severity = row.get("severity")

        if status:
            by_status[status] = by_status.get(status, 0) + 1

        if severity:
            by_severity[severity] = by_severity.get(severity, 0) + 1

    return {
        "client_id": client_id,
        "total_cases": len(summaries),
        "by_status": by_status,
        "by_severity": by_severity,
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
    client_id = _client_id_from_key(x_api_key)

    rows = get_case_summaries(
        client_id=client_id,
        status=status,
        severity=severity,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )

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
    client_id = _client_id_from_key(x_api_key)

    rows = get_case_summaries(
        client_id=client_id,
        status=status,
        severity=severity,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )

    return rows


# =========================
# 4️⃣ DOSSIER CASE
# =========================
@router.get("/cases/{decision_id}/dossier")
def get_case_dossier(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case, _auth = _load_authorized_case(decision_id, x_api_key)

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
    case, _auth = _load_authorized_case(decision_id, x_api_key)

    dossier = build_dossier_payload(case)
    recomputed_hash = compute_dossier_hash(dossier)
    stored_hash = case.get("dossier_hash")

    return {
        "decision_id": case.get("decision_id"),
        "client_id": case.get("client_id"),
        "module": case.get("module"),
        "verified": stored_hash == recomputed_hash,
        "stored_hash": stored_hash,
        "recomputed_hash": recomputed_hash,
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
    case, _auth = _load_authorized_case(decision_id, x_api_key)

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
    case, _auth = _load_authorized_case(decision_id, x_api_key)
    return case


# =========================
# 7️⃣bis SUMMARY CASE
# =========================
@router.get("/cases/{decision_id}/summary")
def get_case_summary(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case, _auth = _load_authorized_case(decision_id, x_api_key)

    timeline = get_case_timeline_from_ledger(decision_id)

    if not timeline:
        timeline = get_case_timeline(decision_id)

    return _build_case_summary_response(case, timeline)


# =========================
# 8️⃣ REVIEW MANUALE
# =========================
@router.post("/cases/{decision_id}/review")
def review_case(
    decision_id: str,
    request: ReviewRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case, auth = _load_authorized_case(decision_id, x_api_key)
    _require_reviewer(auth)

    client_id = case.get("client_id")
    reviewer_id = auth.get("client_id")
    action = request.action.upper()

    ledger_entry = append_ledger_entry(
        build_canonical_ledger_data(
            event_type="HUMAN_REVIEW",
            decision_id=decision_id,
            client_id=client_id,
            module=case.get("module"),
            review_action=action,
            reviewer_id=reviewer_id,
            reason=request.reason,
            metadata={},
        )
    )

    insert_review_action(
        decision_id=decision_id,
        client_id=client_id,
        reviewer_id=reviewer_id,
        action=action,
        reason=request.reason,
        ledger_hash=ledger_entry.get("hash"),
    )

    return {
        "decision_id": decision_id,
        "client_id": client_id,
        "review_action": action,
        "reason": request.reason,
        "status": "RECORDED",
        "ledger_hash": ledger_entry.get("hash"),
    }


# =========================
# 8️⃣bis ADMIN OVERRIDE
# =========================
@router.post("/cases/{decision_id}/admin-override")
def admin_override_case(
    decision_id: str,
    request: AdminOverrideRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case, auth = _load_authorized_case(decision_id, x_api_key)
    _require_super_admin(auth)

    reason = request.reason.strip()
    if len(reason) < 5:
        raise HTTPException(status_code=400, detail="Reason must be at least 5 characters")

    client_id = case.get("client_id")
    reviewer_id = auth.get("client_id")
    action = request.action.upper()

    timeline = get_case_timeline_from_ledger(decision_id)

    if not timeline:
        timeline = get_case_timeline(decision_id)

    previous_status = case.get("status")

    if timeline:
        timeline_items = timeline.get("timeline", [])
        state_events = [
            item for item in timeline_items
            if item.get("type") in {"DECISION", "REVIEW", "OVERRIDE"}
        ]
        if state_events:
            latest_state_event = state_events[-1]
            latest_data = latest_state_event.get("data", {})
            previous_status = (
                latest_data.get("action")
                or latest_data.get("status")
                or previous_status
            )

    ledger_entry = append_ledger_entry(
        build_canonical_ledger_data(
            event_type="ADMIN_OVERRIDE",
            decision_id=decision_id,
            client_id=client_id,
            module=case.get("module"),
            review_action=action,
            reviewer_id=reviewer_id,
            reason=reason,
            metadata={
                "override_type": request.override_type,
                "previous_status": previous_status,
            },
        )
    )

    insert_review_action(
        decision_id=decision_id,
        client_id=client_id,
        reviewer_id=reviewer_id,
        action=action,
        reason=reason,
        ledger_hash=ledger_entry.get("hash"),
    )

    return {
        "decision_id": decision_id,
        "client_id": client_id,
        "override_action": action,
        "reason": reason,
        "override_type": request.override_type,
        "previous_status": previous_status,
        "status": "RECORDED",
        "ledger_hash": ledger_entry.get("hash"),
    }


# =========================
# 9️⃣ LIST REVIEW PER CASE
# =========================
@router.get("/cases/{decision_id}/reviews")
def get_case_reviews(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case, _auth = _load_authorized_case(decision_id, x_api_key)

    reviews = get_reviews_by_decision_id(decision_id)

    return {
        "decision_id": decision_id,
        "client_id": case.get("client_id"),
        "reviews": reviews,
        "count": len(reviews),
    }


# =========================
# 🔟 TIMELINE CASE
# =========================
@router.get("/cases/{decision_id}/timeline")
def get_timeline(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    case, _auth = _load_authorized_case(decision_id, x_api_key)

    timeline = get_case_timeline_from_ledger(decision_id)

    if not timeline:
        timeline = get_case_timeline(decision_id)

    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")

    return {
        **timeline,
        "client_id": case.get("client_id"),
    }
