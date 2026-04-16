import json
import hashlib
import os
import uuid
from datetime import datetime, timezone

LEDGER_PATH = "runtime/logs/ledger_chain.jsonl"
LEDGER_CHECKPOINTS_PATH = "runtime/logs/ledger_checkpoints.jsonl"
LEDGER_ANCHORS_DIR = "runtime/anchors"
LEDGER_PUBLIC_TIMESTAMPS_DIR = "runtime/public_timestamps"
LEDGER_EXTERNAL_ANCHOR_DIR = os.getenv("LEDGER_EXTERNAL_ANCHOR_DIR")

EVENT_TYPE_ENGINE_DECISION = "ENGINE_DECISION"
EVENT_TYPE_HUMAN_REVIEW = "HUMAN_REVIEW"
EVENT_TYPE_ADMIN_OVERRIDE = "ADMIN_OVERRIDE"

ALLOWED_EVENT_TYPES = {
    EVENT_TYPE_ENGINE_DECISION,
    EVENT_TYPE_HUMAN_REVIEW,
    EVENT_TYPE_ADMIN_OVERRIDE,
}

ALLOWED_DECISION_STATUSES = {
    "APPROVED",
    "REJECTED",
    "WARNING",
    "PENDING",
}

ALLOWED_REVIEW_ACTIONS = {
    "APPROVED",
    "REJECTED",
}

ALLOWED_SEVERITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

CANONICAL_LEDGER_KEYS = [
    "event_type",
    "decision_id",
    "client_id",
    "module",
    "status",
    "severity",
    "risk_score",
    "decision_code",
    "review_action",
    "reviewer_id",
    "reason",
    "metadata",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _hash_record(record: dict) -> str:
    record_str = json.dumps(record, sort_keys=True).encode()
    return hashlib.sha256(record_str).hexdigest()


def _safe_ts_for_filename(ts: str) -> str:
    return ts.replace(":", "-").replace(".", "-")


def _write_json_file(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def _read_json_file(path: str) -> dict | None:
    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        return json.load(f)


def _get_last_hash() -> str:
    if not os.path.exists(LEDGER_PATH):
        return "GENESIS"

    with open(LEDGER_PATH, "r") as f:
        lines = f.readlines()
        if not lines:
            return "GENESIS"

        last_record = json.loads(lines[-1])
        return last_record.get("hash", "GENESIS")


def _normalize_upper(value: str | None) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError("Expected string value")

    value = value.strip()
    if not value:
        return None

    return value.upper()


def _validate_event_type(event_type: str) -> None:
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type: {event_type}. "
            f"Allowed values: {sorted(ALLOWED_EVENT_TYPES)}"
        )


def _normalize_metadata(metadata: dict | None) -> dict:
    if metadata is None:
        return {}

    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dict")

    return metadata


def _normalize_and_validate_status(status: str | None) -> str | None:
    normalized = _normalize_upper(status)

    if normalized is None:
        return None

    if normalized not in ALLOWED_DECISION_STATUSES:
        raise ValueError(
            f"Invalid status: {normalized}. "
            f"Allowed values: {sorted(ALLOWED_DECISION_STATUSES)}"
        )

    return normalized


def _normalize_and_validate_review_action(review_action: str | None) -> str | None:
    normalized = _normalize_upper(review_action)

    if normalized is None:
        return None

    if normalized not in ALLOWED_REVIEW_ACTIONS:
        raise ValueError(
            f"Invalid review_action: {normalized}. "
            f"Allowed values: {sorted(ALLOWED_REVIEW_ACTIONS)}"
        )

    return normalized


def _normalize_and_validate_severity(severity: str | None) -> str | None:
    normalized = _normalize_upper(severity)

    if normalized is None:
        return None

    if normalized not in ALLOWED_SEVERITIES:
        raise ValueError(
            f"Invalid severity: {normalized}. "
            f"Allowed values: {sorted(ALLOWED_SEVERITIES)}"
        )

    return normalized


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
    _validate_event_type(event_type)

    status = _normalize_and_validate_status(status)
    review_action = _normalize_and_validate_review_action(review_action)
    severity = _normalize_and_validate_severity(severity)
    metadata = _normalize_metadata(metadata)

    if event_type == EVENT_TYPE_ENGINE_DECISION:
        if not decision_id:
            raise ValueError("decision_id required for ENGINE_DECISION")
        if not client_id:
            raise ValueError("client_id required for ENGINE_DECISION")
        if not module:
            raise ValueError("module required for ENGINE_DECISION")
        if not status:
            raise ValueError("status required for ENGINE_DECISION")

    if event_type == EVENT_TYPE_HUMAN_REVIEW:
        if not decision_id:
            raise ValueError("decision_id required for HUMAN_REVIEW")
        if not client_id:
            raise ValueError("client_id required for HUMAN_REVIEW")
        if not module:
            raise ValueError("module required for HUMAN_REVIEW")
        if not review_action:
            raise ValueError("review_action required for HUMAN_REVIEW")
        if not reviewer_id:
            raise ValueError("reviewer_id required for HUMAN_REVIEW")

    if event_type == EVENT_TYPE_ADMIN_OVERRIDE:
        if not decision_id:
            raise ValueError("decision_id required for ADMIN_OVERRIDE")
        if not client_id:
            raise ValueError("client_id required for ADMIN_OVERRIDE")
        if not module:
            raise ValueError("module required for ADMIN_OVERRIDE")
        if not review_action:
            raise ValueError("review_action required for ADMIN_OVERRIDE")
        if not reviewer_id:
            raise ValueError("reviewer_id required for ADMIN_OVERRIDE")
        if not reason or len(reason.strip()) < 5:
            raise ValueError("reason required for ADMIN_OVERRIDE")

        if "override_type" not in metadata:
            raise ValueError("override_type required in metadata")

        if "previous_status" not in metadata:
            raise ValueError("previous_status required in metadata")

    canonical_status = (
        review_action
        if event_type in {EVENT_TYPE_HUMAN_REVIEW, EVENT_TYPE_ADMIN_OVERRIDE}
        else status
    )

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
        "metadata": metadata,
    }


def _is_canonical_ledger_data(data: dict) -> bool:
    if not isinstance(data, dict):
        return False

    event_type = data.get("event_type")
    if event_type not in ALLOWED_EVENT_TYPES:
        return False

    for key in CANONICAL_LEDGER_KEYS:
        if key not in data:
            return False

    if not isinstance(data.get("metadata"), dict):
        return False

    return True


def append_ledger_entry(data: dict) -> dict:
    if not _is_canonical_ledger_data(data):
        raise ValueError("append_ledger_entry requires canonical ledger data")

    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)

    prev_hash = _get_last_hash()
    if not prev_hash:
        raise ValueError("Invalid previous hash state")

    entry = {
        "timestamp": _utc_now_iso(),
        "data": data,
        "prev_hash": prev_hash,
    }

    entry_hash = _hash_record(entry)
    entry["hash"] = entry_hash

    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def get_ledger_entries() -> list[dict]:
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
    entries = get_ledger_entries()

    return [
        entry
        for entry in entries
        if entry.get("data", {}).get("decision_id") == decision_id
    ]


def verify_chain() -> bool:
    if not os.path.exists(LEDGER_PATH):
        return True

    with open(LEDGER_PATH, "r") as f:
        lines = f.readlines()

    prev_hash = "GENESIS"

    for line in lines:
        record = json.loads(line)

        if record.get("prev_hash") != prev_hash:
            return False

        record_copy = {
            "timestamp": record["timestamp"],
            "data": record["data"],
            "prev_hash": record["prev_hash"],
        }

        if _hash_record(record_copy) != record.get("hash"):
            return False

        prev_hash = record["hash"]

    return True


# =========================
# LEDGER CHECKPOINTS
# =========================

def build_ledger_checkpoint() -> dict:
    entries = get_ledger_entries()
    entries_count = len(entries)
    ledger_last_hash = _get_last_hash()

    checkpoint = {
        "checkpoint_id": str(uuid.uuid4()),
        "created_at": _utc_now_iso(),
        "entries_count": entries_count,
        "ledger_last_hash": ledger_last_hash,
    }

    checkpoint["checkpoint_hash"] = _hash_record(checkpoint)
    return checkpoint


def append_ledger_checkpoint() -> dict:
    os.makedirs(os.path.dirname(LEDGER_CHECKPOINTS_PATH), exist_ok=True)

    checkpoint = build_ledger_checkpoint()

    with open(LEDGER_CHECKPOINTS_PATH, "a") as f:
        f.write(json.dumps(checkpoint) + "\n")

    return checkpoint


def get_ledger_checkpoints() -> list[dict]:
    if not os.path.exists(LEDGER_CHECKPOINTS_PATH):
        return []

    with open(LEDGER_CHECKPOINTS_PATH, "r") as f:
        lines = f.readlines()

    checkpoints = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            checkpoints.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return checkpoints


def get_latest_ledger_checkpoint() -> dict | None:
    checkpoints = get_ledger_checkpoints()
    if not checkpoints:
        return None
    return checkpoints[-1]


# =========================
# CHECKPOINT EXPORT / ANCHOR
# =========================

def export_latest_checkpoint_anchor() -> dict:
    checkpoint = get_latest_ledger_checkpoint()
    if not checkpoint:
        raise ValueError("No ledger checkpoint found")

    os.makedirs(LEDGER_ANCHORS_DIR, exist_ok=True)

    safe_ts = _safe_ts_for_filename(checkpoint["created_at"])
    file_name = f"ledger_anchor_{safe_ts}.json"

    local_path = os.path.join(LEDGER_ANCHORS_DIR, file_name)
    _write_json_file(local_path, checkpoint)

    external_path = None
    if LEDGER_EXTERNAL_ANCHOR_DIR:
        os.makedirs(LEDGER_EXTERNAL_ANCHOR_DIR, exist_ok=True)
        external_path = os.path.join(LEDGER_EXTERNAL_ANCHOR_DIR, file_name)
        _write_json_file(external_path, checkpoint)

    return {
        "status": "EXPORTED",
        "file_name": file_name,
        "local_path": local_path,
        "external_path": external_path,
        "checkpoint": checkpoint,
    }


def get_anchor_file_hash(anchor_path: str) -> str:
    if not os.path.exists(anchor_path):
        raise ValueError("Anchor file not found")

    with open(anchor_path, "rb") as f:
        content = f.read()

    return _hash_bytes(content)


# =========================
# PUBLIC TIMESTAMP PREP
# =========================

def prepare_latest_public_timestamp_receipt() -> dict:
    export_result = export_latest_checkpoint_anchor()
    checkpoint = export_result["checkpoint"]
    anchor_path = export_result["local_path"]

    anchor_sha256 = get_anchor_file_hash(anchor_path)

    receipt = {
        "receipt_id": str(uuid.uuid4()),
        "created_at": _utc_now_iso(),
        "anchor_file_name": export_result["file_name"],
        "anchor_local_path": export_result["local_path"],
        "anchor_external_path": export_result["external_path"],
        "anchor_sha256": anchor_sha256,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "checkpoint_hash": checkpoint["checkpoint_hash"],
        "ledger_last_hash": checkpoint["ledger_last_hash"],
        "entries_count": checkpoint["entries_count"],
        "timestamp_provider": None,
        "timestamp_proof": None,
        "timestamp_status": "PREPARED",
    }

    os.makedirs(LEDGER_PUBLIC_TIMESTAMPS_DIR, exist_ok=True)

    safe_ts = _safe_ts_for_filename(receipt["created_at"])
    receipt_file_name = f"public_timestamp_receipt_{safe_ts}.json"
    receipt_path = os.path.join(LEDGER_PUBLIC_TIMESTAMPS_DIR, receipt_file_name)

    _write_json_file(receipt_path, receipt)

    return {
        "status": "PREPARED",
        "receipt_file_name": receipt_file_name,
        "receipt_path": receipt_path,
        "receipt": receipt,
    }


def get_public_timestamp_receipts() -> list[dict]:
    if not os.path.exists(LEDGER_PUBLIC_TIMESTAMPS_DIR):
        return []

    receipts = []

    for name in sorted(os.listdir(LEDGER_PUBLIC_TIMESTAMPS_DIR)):
        if not name.endswith(".json"):
            continue

        path = os.path.join(LEDGER_PUBLIC_TIMESTAMPS_DIR, name)
        receipt = _read_json_file(path)
        if receipt:
            receipts.append(receipt)

    return receipts


def get_latest_public_timestamp_receipt() -> dict | None:
    receipts = get_public_timestamp_receipts()
    if not receipts:
        return None
    return receipts[-1]
