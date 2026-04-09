from datetime import datetime
from typing import List, Dict, Any
import json
import os
from uuid import uuid4

from src.regulatory.models import RegulatoryDelta
from src.regulatory.impact_engine import detect_client_impacts
from src.regulatory.versioning_service import freeze_and_create_rule_version
from src.regulatory.validation_queue import create_legal_review_tasks

EVENTS_FILE = "src/shared/regulatory_events.json"


def _load_events() -> Dict[str, Any]:
    if not os.path.exists(EVENTS_FILE):
        return {"events": []}

    with open(EVENTS_FILE, "r") as f:
        return json.load(f)


def _save_events(data: Dict[str, Any]) -> None:
    with open(EVENTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


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

        # Detect client impacts (pre-analysis only)
        impacts = detect_client_impacts(delta, client_records)

        # Create legal review task
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
