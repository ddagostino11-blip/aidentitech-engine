from typing import Dict, Any
from datetime import datetime

from src.services.event_store import load_event_store, save_event_store
from src.services.state_store import update_domain_state


def _update_regulatory_state(event: Dict[str, Any], timestamp: str) -> None:
    domain = event.get("domain")

    if not domain:
        return

    update_domain_state(domain, {
        "status": "ACTIVE",
        "freeze_active": False,
        "freeze_reason": None,
        "freeze_timestamp": None,
        "triggered_by": event.get("event_id"),
        "last_updated": timestamp,
    })

    print(f"[Executor] UNFREEZE applied to {domain}")


def _repair_historical_approved_event(event: Dict[str, Any]) -> bool:
    if event.get("status") != "legal_approved":
        return False

    if event.get("freeze_active") is not True:
        return False

    repair_timestamp = datetime.utcnow().isoformat()

    event["freeze_active"] = False
    event["freeze_reason"] = None
    event["freeze_timestamp"] = None

    if not event.get("freeze_released_at"):
        event["freeze_released_at"] = repair_timestamp

    return True


def _should_process_approved_event(event: Dict[str, Any]) -> bool:
    return (
        event.get("status") == "legal_approved"
        and event.get("versioning_status") == "pending_versioning"
        and event.get("processed_at") is None
    )


def _process_single_approved_event(event: Dict[str, Any]) -> None:
    process_timestamp = datetime.utcnow().isoformat()

    # 1. versioning completato
    event["versioning_status"] = "versioned"

    # 2. update regulatory state reale (con UNFREEZE)
    _update_regulatory_state(event, process_timestamp)
    event["regulatory_state_updated"] = True

    # 3. allinea storico evento
    event["freeze_active"] = False
    event["freeze_reason"] = None
    event["freeze_timestamp"] = None
    event["freeze_released_at"] = process_timestamp

    # 4. trigger downstream
    event["revalidation_triggered"] = True

    # 5. audit finale tecnico
    event["processed_at"] = process_timestamp

    print(f"[Executor] Event {event['event_id']} fully processed")


def process_approved_events() -> Dict[str, Any]:
    store = load_event_store()
    events = store.get("events", [])

    processed = []
    repaired = []

    # 1. repair retroattivo separato
    for event in events:
        if _repair_historical_approved_event(event):
            repaired.append(event["event_id"])

    # 2. process solo eventi realmente pending_versioning e non già processati
    for event in events:
        if not _should_process_approved_event(event):
            continue

        _process_single_approved_event(event)
        processed.append(event["event_id"])

    save_event_store(store)

    return {
        "processed_events": len(processed),
        "event_ids": processed,
        "repaired_events": len(repaired),
        "repaired_event_ids": repaired
    }
