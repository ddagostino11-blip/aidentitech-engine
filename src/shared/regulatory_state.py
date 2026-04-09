import json
from pathlib import Path
from typing import Dict, Any

STATE_FILE = "src/shared/regulatory_state.json"


def load_regulatory_state() -> Dict[str, Any]:
    state_path = Path(STATE_FILE)

    if not state_path.exists():
        return {}

    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_domain_state(domain: str) -> Dict[str, Any]:
    state = load_regulatory_state()
    return state.get(domain, {})


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
        "status": domain_state.get("status")
    }