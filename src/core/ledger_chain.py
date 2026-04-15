import json
import hashlib
import os
from datetime import datetime

LEDGER_PATH = "runtime/logs/ledger_chain.jsonl"


def _hash_record(record: dict) -> str:
    """Compute SHA256 hash of a record (deterministic)."""
    record_str = json.dumps(record, sort_keys=True).encode()
    return hashlib.sha256(record_str).hexdigest()


def _get_last_hash() -> str:
    """Return hash of last record in ledger, or 'GENESIS' if empty."""
    if not os.path.exists(LEDGER_PATH):
        return "GENESIS"

    with open(LEDGER_PATH, "r") as f:
        lines = f.readlines()
        if not lines:
            return "GENESIS"

        last_record = json.loads(lines[-1])
        return last_record.get("hash", "GENESIS")


def build_canonical_ledger_data(
    event_type: str,
    decision_id: str | None = None,
    client_id: str | None = None,
    module: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    risk_score: int | float | None = None,
    decision_code: str | None = None,
    review_action: str | None = None,
    reviewer_id: str | None = None,
    reason: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Build canonical ledger payload for all new entries.

    All keys are always present to keep the ledger schema uniform.
    """
    canonical_status = review_action if event_type == "HUMAN_REVIEW" else status

    return {
        "event_type": event_type,
        "decision_id": decision_id,
        "client_id": client_id,
        "module": module,
        "status": canonical_status,
        "severity": severity,
        "risk_score": risk_score,
        "decision_code": decision_code,
        "review_action": review_action,
        "reviewer_id": reviewer_id,
        "reason": reason,
        "metadata": metadata or {},
    }


def append_ledger_entry(data: dict) -> dict:
    """Append a new entry to the ledger with chaining."""
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)

    prev_hash = _get_last_hash()

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
        "prev_hash": prev_hash,
    }

    entry_hash = _hash_record(entry)
    entry["hash"] = entry_hash

    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def get_ledger_entries() -> list[dict]:
    """Return all ledger entries in append order."""
    if not os.path.exists(LEDGER_PATH):
        return []

    with open(LEDGER_PATH, "r") as f:
        lines = f.readlines()

    entries = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return entries


def get_ledger_entries_by_decision_id(decision_id: str) -> list[dict]:
    """Return all ledger entries whose payload references the given decision_id."""
    entries = get_ledger_entries()

    return [
        entry
        for entry in entries
        if entry.get("data", {}).get("decision_id") == decision_id
    ]


def verify_chain() -> bool:
    """Verify integrity of the entire ledger chain."""
    if not os.path.exists(LEDGER_PATH):
        return True

    with open(LEDGER_PATH, "r") as f:
        lines = f.readlines()

    prev_hash = "GENESIS"

    for line in lines:
        record = json.loads(line)

        expected_prev = record.get("prev_hash")
        if expected_prev != prev_hash:
            return False

        record_copy = {
            "timestamp": record["timestamp"],
            "data": record["data"],
            "prev_hash": record["prev_hash"],
        }

        computed_hash = _hash_record(record_copy)

        if computed_hash != record.get("hash"):
            return False

        prev_hash = record["hash"]

    return True
