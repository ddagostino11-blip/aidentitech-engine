import json
import os
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
