import json
from typing import Dict, Any, List

EVENTS_FILE = "src/shared/regulatory_events.json"


def _load_events() -> List[Dict[str, Any]]:
    with open(EVENTS_FILE, "r") as f:
        data = json.load(f)
    return data.get("events", [])


def _save_events(events: List[Dict[str, Any]]) -> None:
    with open(EVENTS_FILE, "w") as f:
        json.dump({"events": events}, f, indent=2)


def process_approved_events() -> Dict[str, Any]:
    events = _load_events()
    processed = []

    for event in events:
        if event.get("status") != "legal_approved":
            continue

        if event.get("versioning_status") != "pending_versioning":
            continue

        # Simulazione versioning completato
        event["versioning_status"] = "versioned"
        event["regulatory_state_updated"] = True
        event["revalidation_triggered"] = True

        processed.append(event["event_id"])

        print(f"[Executor] Event {event['event_id']} fully processed")

    _save_events(events)

    return {
        "processed_events": len(processed),
        "event_ids": processed
    }
