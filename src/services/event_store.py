import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

EVENTS_FILE = "src/shared/regulatory_events.json"


def load_event_store() -> Dict[str, Any]:
    if not os.path.exists(EVENTS_FILE):
        return {"events": []}

    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_event_store(store: Dict[str, Any]) -> None:
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def get_events() -> List[Dict[str, Any]]:
    store = load_event_store()
    return store.get("events", [])


def find_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    events = get_events()
    for event in events:
        if event.get("event_id") == event_id:
            return event
    return None


def find_open_event(
    client_id: str,
    product_id: str,
    domain: str,
    status: str = "pending_legal_review",
) -> Optional[Dict[str, Any]]:
    events = get_events()

    for event in events:
        if (
            event.get("client_id") == client_id
            and event.get("product_id") == product_id
            and event.get("domain") == domain
            and event.get("status") == status
        ):
            return event

    return None


def filter_events(
    status: Optional[str] = None,
    domain: Optional[str] = None
) -> List[Dict[str, Any]]:
    events = get_events()

    if status:
        events = [event for event in events if event.get("status") == status]

    if domain:
        events = [event for event in events if event.get("domain") == domain]

    return events


def append_event(event: Dict[str, Any]) -> None:
    store = load_event_store()
    store.setdefault("events", []).append(event)
    save_event_store(store)


def update_event(updated_event: Dict[str, Any]) -> bool:
    store = load_event_store()
    events = store.get("events", [])

    for index, event in enumerate(events):
        if event.get("event_id") == updated_event.get("event_id"):
            events[index] = updated_event
            save_event_store(store)
            return True

    return False


def generate_event_id() -> str:
    return f"event-{uuid.uuid4()}"


def create_regulatory_event(
    domain: str,
    rule_id: str,
    change_type: str,
    impact_level: str,
    priority: str,
    jurisdiction: str = "EU",
    delta_id: Optional[str] = None,
    impacts_detected: int = 0,
    freeze_active: bool = False,
    freeze_reason: Optional[str] = None,
    legal_tasks: Optional[List[Dict[str, Any]]] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    event = {
        "event_id": generate_event_id(),
        "delta_id": delta_id or str(uuid.uuid4()),
        "domain": domain,
        "jurisdiction": jurisdiction,
        "rule_id": rule_id,
        "change_type": change_type,
        "impact_level": impact_level,
        "priority": priority,
        "status": "pending_legal_review",
        "freeze_active": freeze_active,
        "freeze_reason": freeze_reason,
        "created_at": datetime.utcnow().isoformat(),
        "legal_tasks": legal_tasks or [],
        "impacts_detected": impacts_detected,
    }

    if extra_fields:
        event.update(extra_fields)

    append_event(event)
    return event
