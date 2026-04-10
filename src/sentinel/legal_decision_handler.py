from typing import Dict, Any, Optional
from datetime import datetime

from src.sentinel.post_approval_executor import process_approved_events
from src.services.event_store import (
    load_event_store,
    save_event_store,
    find_event_by_id,
)


def _find_event(store: Dict[str, Any], event_id: str) -> Optional[Dict[str, Any]]:
    for event in store.get("events", []):
        if event.get("event_id") == event_id:
            return event
    return None


def handle_legal_decision(
    event_id: str,
    decision: str,   # approve | reject | defer
    reviewer_name: str = "LEGAL_TEAM",
    notes: str | None = None
) -> Dict[str, Any]:
    store = load_event_store()
    event = _find_event(store, event_id)

    if not event:
        return {"error": "event_not_found"}

    if event.get("status") != "pending_legal_review":
        return {"error": "invalid_state", "current_status": event.get("status")}

    decision = decision.lower().strip()
    now = datetime.utcnow().isoformat()

    event["legal_review"] = {
        "decision": decision,
        "reviewer_name": reviewer_name,
        "notes": notes,
        "reviewed_at": now
    }

    executor_result = None

    if decision == "approve":
        event["status"] = "legal_approved"
        event["approved_at"] = now
        event["versioning_status"] = "pending_versioning"

        print(f"[Sentinel] Event {event_id} APPROVED by {reviewer_name}")

        save_event_store(store)

        executor_result = process_approved_events()

        store = load_event_store()
        event = _find_event(store, event_id)

    elif decision == "reject":
        event["status"] = "legal_rejected"
        event["rejected_at"] = now

        if event.get("freeze_active") is True:
            event["freeze_active"] = False
            event["freeze_released_at"] = now

        print(f"[Sentinel] Event {event_id} REJECTED by {reviewer_name}")
        save_event_store(store)

    elif decision == "defer":
        event["status"] = "legal_deferred"
        event["deferred_at"] = now

        print(f"[Sentinel] Event {event_id} DEFERRED by {reviewer_name}")
        save_event_store(store)

    else:
        return {"error": "invalid_decision"}

    response = {
        "event_id": event_id,
        "status": event["status"],
        "legal_review": event.get("legal_review")
    }

    if executor_result is not None:
        response["executor_result"] = executor_result

    if event.get("versioning_status") is not None:
        response["versioning_status"] = event.get("versioning_status")

    if event.get("processed_at") is not None:
        response["processed_at"] = event.get("processed_at")

    return response
