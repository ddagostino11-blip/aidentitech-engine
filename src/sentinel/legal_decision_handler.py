from typing import Dict, Any, Optional
import json
import os
from datetime import datetime

from src.sentinel.post_approval_executor import process_approved_events

EVENTS_FILE = "src/shared/regulatory_events.json"


def _load_events() -> Dict[str, Any]:
    if not os.path.exists(EVENTS_FILE):
        return {"events": []}

    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_events(data: Dict[str, Any]) -> None:
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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
    store = _load_events()
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

        _save_events(store)

        executor_result = process_approved_events()

        store = _load_events()
        event = _find_event(store, event_id)

    elif decision == "reject":
        event["status"] = "legal_rejected"
        event["rejected_at"] = now

        if event.get("freeze_active") is True:
            event["freeze_active"] = False
            event["freeze_released_at"] = now

        print(f"[Sentinel] Event {event_id} REJECTED by {reviewer_name}")
        _save_events(store)

    elif decision == "defer":
        event["status"] = "legal_deferred"
        event["deferred_at"] = now

        print(f"[Sentinel] Event {event_id} DEFERRED by {reviewer_name}")
        _save_events(store)

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