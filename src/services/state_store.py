import json
import os
from typing import Dict, Any, Optional

STATE_FILE = "src/shared/regulatory_state.json"


def load_state_store() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state_store(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_domain_state(domain: str) -> Dict[str, Any]:
    state = load_state_store()
    return state.get(domain, {})


def update_domain_state(domain: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state_store()
    current = state.get(domain, {})

    current.update(updates)
    state[domain] = current

    save_state_store(state)
    return current


def is_domain_frozen(domain: str) -> bool:
    domain_state = get_domain_state(domain)
    return bool(domain_state.get("freeze_active", False))


def get_freeze_metadata(domain: str) -> Dict[str, Any]:
    domain_state = get_domain_state(domain)

    return {
        "freeze_active": domain_state.get("freeze_active", False),
        "freeze_reason": domain_state.get("freeze_reason"),
        "freeze_timestamp": domain_state.get("freeze_timestamp"),
        "triggered_by": domain_state.get("triggered_by"),
        "status": domain_state.get("status"),
    }
