from datetime import datetime
from typing import List, Dict, Any
import json
import os
from uuid import uuid4

from src.regulatory.models import RegulatoryDelta
from src.regulatory.impact_engine import detect_client_impacts
from src.regulatory.validation_queue import create_legal_review_tasks

EVENTS_FILE = "src/shared/regulatory_events.json"
STATE_FILE = "src/shared/regulatory_state.json"


def _load_events() -> Dict[str, Any]:
    if not os.path.exists(EVENTS_FILE):
        return {"events": []}

    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_events(data: Dict[str, Any]) -> None:
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _priority_from_impact(impact: str) -> str:
    mapping = {
        "CRITICAL": "CRITICAL",
        "HIGH": "HIGH",
        "MEDIUM": "MEDIUM",
        "LOW": "LOW"
    }
    return mapping.get(impact, "MEDIUM")


def _should_freeze(delta: RegulatoryDelta) -> bool:
    return delta.impact_level in ["HIGH", "CRITICAL"]


def apply_pre_legal_freeze(event: Dict[str, Any]) -> None:
    state = _load_state()
    domain = event.get("domain")

    if not domain:
        return

    if domain not in state:
        state[domain] = {}

    if event.get("freeze_active"):
        state[domain]["freeze_active"] = True
        state[domain]["freeze_reason"] = event.get("freeze_reason")
        state[domain]["freeze_timestamp"] = datetime.utcnow().isoformat()
        state[domain]["status"] = "FROZEN"
        state[domain]["triggered_by"] = "SENTINEL"

        # aggiorna anche metadati sentinel se presenti/necessari
        sentinel_block = state[domain].get("sentinel", {})
        sentinel_block["monitoring"] = True
        sentinel_block["priority"] = event.get("priority", "HIGH")
        sentinel_block["last_check"] = datetime.utcnow().isoformat()
        state[domain]["sentinel"] = sentinel_block
    else:
        # se non c'è freeze, aggiorna solo il last_check sentinel
        sentinel_block = state[domain].get("sentinel", {})
        sentinel_block["monitoring"] = True
        sentinel_block["priority"] = event.get("priority", "MEDIUM")
        sentinel_block["last_check"] = datetime.utcnow().isoformat()
        state[domain]["sentinel"] = sentinel_block

    _save_state(state)


def process_deltas(
    deltas: List[RegulatoryDelta],
    client_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store = _load_events()
    created_events = []

    for delta in deltas:
        event_id = f"event-{uuid4()}"
        priority = _priority_from_impact(delta.impact_level)
        freeze_active = _should_freeze(delta)

        impacts = detect_client_impacts(delta, client_records)
        legal_tasks = create_legal_review_tasks([delta])

        event = {
            "event_id": event_id,
            "delta_id": delta.delta_id,
            "domain": delta.domain,
            "jurisdiction": delta.jurisdiction,
            "rule_id": delta.rule_id,
            "change_type": delta.change_type,
            "impact_level": delta.impact_level,
            "priority": priority,
            "status": "pending_legal_review",
            "freeze_active": freeze_active,
            "freeze_reason": "auto_regulatory_high_impact" if freeze_active else None,
            "created_at": datetime.utcnow().isoformat(),
            "legal_tasks": [
                {
                    "review_id": t.review_id,
                    "status": t.status,
                    "priority": t.priority
                }
                for t in legal_tasks
            ],
            "impacts_detected": len(impacts),
        }

        apply_pre_legal_freeze(event)

        store["events"].append(event)
        created_events.append(event)

        print(f"[Sentinel] Event created: {event_id} ({delta.rule_id})")

        if freeze_active:
            print(f"[Sentinel] PREVENTIVE FREEZE activated for {delta.rule_id}")

    _save_events(store)

    return {
        "created_events": len(created_events),
        "events": created_events
    }
