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

        # Recompute hash
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
