from fastapi import APIRouter, HTTPException

from src.core.db import (
    get_case_by_decision_id,
    get_latest_review_by_decision_id,
)

router = APIRouter(tags=["verify"])


@router.get("/verify/{decision_id}")
def verify_case(decision_id: str):
    case = get_case_by_decision_id(decision_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    latest_review = get_latest_review_by_decision_id(decision_id)

    engine_status = case.get("status")
    final_status = latest_review.get("action") if latest_review else engine_status
    has_admin_override = bool(latest_review)
    latest_event_timestamp = latest_review.get("created_at") if latest_review else case.get("decision_timestamp")

    return {
        "verified": True,
        "decision_id": case.get("decision_id"),
        "client_id": case.get("client_id"),
        "module": case.get("module"),
        "engine_status": engine_status,
        "final_status": final_status,
        "severity": case.get("severity"),
        "risk_score": case.get("risk_score"),
        "decision_code": case.get("decision_code"),
        "has_admin_override": has_admin_override,
        "latest_event_timestamp": latest_event_timestamp,
        "ledger_hash": case.get("ledger_hash"),
        "dossier_hash": case.get("dossier_hash"),
    }
