import json
import time
from pathlib import Path
from typing import List, Dict, Any

from src.regulatory.diff_engine import build_regulatory_deltas


REGISTRY_PATH = Path("src/sentinel/source_registry.json")


def load_sources() -> List[Dict[str, Any]]:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("sources", [])


def mock_fetch_regulation(source: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rules": {
            "temperature_warning_high": 6,
            "temperature_critical_high": 20,
            "gmp_required": True
        }
    }


def run_single_check(source: Dict[str, Any]) -> None:
    print(f"[Sentinel] Checking source: {source['source_id']} ({source['domain']})")

    old_structure = {
        "rules": {
            "temperature_warning_high": 8,
            "temperature_critical_high": 25,
            "gmp_required": True
        }
    }

    new_structure = mock_fetch_regulation(source)

    deltas = build_regulatory_deltas(
        old_structure=old_structure,
        new_structure=new_structure,
        document_id=f"DOC-{source['source_id']}",
        source_id=source["source_id"],
        domain=source["domain"],
        jurisdiction=source["region"]
    )

    if deltas:
        print(f"Detected {len(deltas)} changes for {source['source_id']}")
    else:
        print(f"No changes detected for {source['source_id']}")


def run_sentinel_loop() -> None:
    sources = load_sources()

    while True:
        for source in sources:
            if not isinstance(source, dict):
                continue

            if not source.get("monitoring", False):
                continue

            run_single_check(source)

        time.sleep(60)


if __name__ == "__main__":
    run_sentinel_loop()
