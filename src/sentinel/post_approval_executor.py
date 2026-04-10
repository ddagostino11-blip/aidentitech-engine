from typing import Dict, Any
from datetime import datetime

from src.services.event_store import load_event_store, save_event_store
from src.services.state_store import update_domain_state


def _update_regulatory_state(event: Dict[str, Any]) -> None:
    domain = event.get("domain")

    if not domain:
        return

    update_domain_state(domain, {
        "status": "ACTIVE",
        "freeze_active": False,
        "freeze_reason": None,
        "freeze_timestamp": None,
        "triggered_by": event.get("event_id"),
        "last_updated": datetime.utcnow().isoformat(),
    })

    print(f"[Executor] UNFREEZE applied to {domain}")


def process_approved_events() -> Dict[str, Any]:
    store = load_event_store()
    events = store.get("events", [])
    processed = []
    repaired = []

    for event in events:
        # FIX retroattivo per eventi già approvati ma rimasti congelati nello storico
        if event.get("status") == "legal_approved" and event.get("freeze_active") is True:
            event["freeze_active"] = False
            event["freeze_reason"] = None
            event["freeze_timestamp"] = None

            if not event.get("freeze_released_at"):
                event["freeze_released_at"] = datetime.utcnow().isoformat()

            repaired.append(event["event_id"])

        if event.get("status") != "legal_approved":
            continue

        if event.get("versioning_status") != "pending_versioning":
            continue

        # 1. versioning completato
        event["versioning_status"] = "versioned"

        # 2. update regulatory state reale (con UNFREEZE)
        _update_regulatory_state(event)
        event["regulatory_state_updated"] = True

        # 2b. allinea anche lo storico evento
        event["freeze_active"] = False
        event["freeze_reason"] = None
        event["freeze_timestamp"] = None
        event["freeze_released_at"] = datetime.utcnow().isoformat()

        # 3. trigger downstream
        event["revalidation_triggered"] = True

        # 4. audit finale
        event["processed_at"] = datetime.utcnow().isoformat()

        processed.append(event["event_id"])

        print(f"[Executor] Event {event['event_id']} fully processed")

    save_event_store(store)

    return {
        "processed_events": len(processed),
        "event_ids": processed,
        "repaired_events": len(repaired),
        "repaired_event_ids": repaired
    }
