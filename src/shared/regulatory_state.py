import json
from pathlib import Path


def load_regulatory_state() -> dict:
    state_path = Path(__file__).with_name("regulatory_state.json")

    if not state_path.exists():
        return {}

    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)