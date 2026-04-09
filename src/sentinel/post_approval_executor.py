import json
import os
from typing import Dict, Any, List
from datetime import datetime

EVENTS_FILE = "src/shared/regulatory_events.json"
STATE_FILE = "src/shared/regulatory_state.json"


def _load_events() -> List[Dict[str, Any]]:
    with open(EVENTS_FILE, "r") as f:
        data = json.load(f)
    return data.get("events", [])


def _save_events(events: List[Dict[str, Any]]) -> None:
    with open(EVENTS_FILE, "w") as f:
        json.dump({"events": events}, f, indent=2)


def _load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def _save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _update_regulatory_state(event: Dict[str, Any]) -> None:
    state = _load_state()

    domain = event.get("domain")

    if domain not in state:
        state[domain] = {}

    # ✅ UNFREEZE + stato attivo
    state[domain]["status"] = "ACTIVE"
    state[domain]["freeze_active"] = False
    state[domain]["freeze_reason"] = None
    state[domain]["freeze_timestamp"] = None
    state[domain]["triggered_by"] = event.get("event_id")

    # audit
    state[domain]["last_updated"] = datetime.utcnow().isoformat()

    _save_state(state)

    print(f"[Executor] UNFREEZE applied to {domain}")


def process_approved_events() -> Dict[str, Any]:
    events = _load_events()
    processed = []

    for event in events:
        if event.get("status") != "legal_approved":
            continue

        if event.get("versioning_status") != "pending_versioning":
            continue

        # 1. versioning completato
        event["versioning_status"] = "versioned"

        # 2. update regulatory state reale (con UNFREEZE)
        _update_regulatory_state(event)
        event["regulatory_state_updated"] = True

        # 3. trigger downstream
        event["revalidation_triggered"] = True

        # 4. audit finale
        event["processed_at"] = datetime.utcnow().isoformat()

        processed.append(event["event_id"])

        print(f"[Executor] Event {event['event_id']} fully processed")

    _save_events(events)

    return {
        "processed_events": len(processed),
        "event_ids": processed
    }
