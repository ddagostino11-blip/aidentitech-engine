from typing import Dict, Any, Optional
from datetime import datetime

from src.sentinel.post_approval_executor import process_approved_events
from src.services.event_store import (
    load_event_store,
    save_event_store,
)


def _find_event(store: Dict[str, Any], event_id: str) -> Optional[Dict[str, Any]]:
    for event in store.get("events", []):
        if event.get("event_id") == event_id:
            return event
    return None


def _set_legal_tasks_status(event: Dict[str, Any], status: str) -> None:
    for task in event.get("legal_tasks", []):
        task["status"] = status


def _append_audit_entry(
    event: Dict[str, Any],
    action: str,
    actor: str,
    timestamp: str,
    notes: str | None = None
) -> None:
    event.setdefault("audit_trail", []).append(
        {
            "action": action,
            "actor": actor,
            "timestamp": timestamp,
            "notes": notes
        }
    )


def _apply_transition(
    event: Dict[str, Any],
    transition: str,
    actor: str,
    timestamp: str,
    notes: str | None = None
) -> None:
    if transition == "approve":
        event["status"] = "legal_approved"
        event["approved_at"] = timestamp
        event["versioning_status"] = "pending_versioning"
        _set_legal_tasks_status(event, "completed")
        _append_audit_entry(
            event=event,
            action="approved",
            actor=actor,
            timestamp=timestamp,
            notes=notes
        )

    elif transition == "reject":
        event["status"] = "legal_rejected"
        event["rejected_at"] = timestamp
        event["freeze_active"] = True
        if not event.get("freeze_reason"):
            event["freeze_reason"] = "legal_rejected"
        _set_legal_tasks_status(event, "rejected")
        _append_audit_entry(
            event=event,
            action="rejected",
            actor=actor,
            timestamp=timestamp,
            notes=notes
        )

    elif transition == "defer":
        event["status"] = "legal_deferred"
        event["deferred_at"] = timestamp
        event["freeze_active"] = True
        if not event.get("freeze_reason"):
            event["freeze_reason"] = "legal_deferred"
        _set_legal_tasks_status(event, "deferred")
        _append_audit_entry(
            event=event,
            action="deferred",
            actor=actor,
            timestamp=timestamp,
            notes=notes
        )

    elif transition == "reopen":
        event["status"] = "pending_legal_review"
        event["reopened_at"] = timestamp
        event["freeze_active"] = True
        _set_legal_tasks_status(event, "pending_review")
        event["legal_reopen"] = {
            "reviewer_name": actor,
            "notes": notes,
            "reopened_at": timestamp
        }
        _append_audit_entry(
            event=event,
            action="reopened",
            actor=actor,
            timestamp=timestamp,
            notes=notes
        )

    else:
        raise ValueError(f"Unsupported transition: {transition}")


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

    if decision not in {"approve", "reject", "defer"}:
        return {"error": "invalid_decision"}

    event["legal_review"] = {
        "decision": decision,
        "reviewer_name": reviewer_name,
        "notes": notes,
        "reviewed_at": now
    }

    executor_result = None

    _apply_transition(
        event=event,
        transition=decision,
        actor=reviewer_name,
        timestamp=now,
        notes=notes
    )

    if decision == "approve":
        print(f"[Sentinel] Event {event_id} APPROVED by {reviewer_name}")

        save_event_store(store)

        executor_result = process_approved_events()

        store = load_event_store()
        event = _find_event(store, event_id)

    elif decision == "reject":
        print(f"[Sentinel] Event {event_id} REJECTED by {reviewer_name}")
        save_event_store(store)

    elif decision == "defer":
        print(f"[Sentinel] Event {event_id} DEFERRED by {reviewer_name}")
        save_event_store(store)

    response = {
        "event_id": event_id,
        "status": event["status"],
        "legal_review": event.get("legal_review"),
        "freeze_active": event.get("freeze_active"),
        "freeze_reason": event.get("freeze_reason"),
        "legal_tasks": event.get("legal_tasks", []),
        "audit_trail": event.get("audit_trail", []),
    }

    if executor_result is not None:
        response["executor_result"] = executor_result

    if event.get("versioning_status") is not None:
        response["versioning_status"] = event.get("versioning_status")

    if event.get("processed_at") is not None:
        response["processed_at"] = event.get("processed_at")

    if event.get("freeze_released_at") is not None:
        response["freeze_released_at"] = event.get("freeze_released_at")

    return response


def handle_legal_reopen(
    event_id: str,
    reviewer_name: str = "LEGAL_TEAM",
    notes: str | None = None
) -> Dict[str, Any]:
    store = load_event_store()
    event = _find_event(store, event_id)

    if not event:
        return {"error": "event_not_found"}

    if event.get("status") != "legal_deferred":
        return {"error": "invalid_state", "current_status": event.get("status")}

    now = datetime.utcnow().isoformat()

    _apply_transition(
        event=event,
        transition="reopen",
        actor=reviewer_name,
        timestamp=now,
        notes=notes
    )

    print(f"[Sentinel] Event {event_id} REOPENED by {reviewer_name}")
    save_event_store(store)

    return {
        "event_id": event_id,
        "status": event.get("status"),
        "freeze_active": event.get("freeze_active"),
        "freeze_reason": event.get("freeze_reason"),
        "legal_tasks": event.get("legal_tasks", []),
        "legal_reopen": event.get("legal_reopen"),
        "audit_trail": event.get("audit_trail", []),
    }
