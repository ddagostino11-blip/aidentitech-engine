import os
import json

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from src.core.db import list_api_keys, revoke_api_key, rotate_api_key
from src.core.auth import get_client_from_api_key
from src.core.ledger_chain import (
    verify_chain,
    get_ledger_entries_by_decision_id,
)

router = APIRouter(tags=["admin"])

LEDGER_PATH = "runtime/logs/ledger_chain.jsonl"


class RevokeApiKeyRequest(BaseModel):
    api_key: str


class RotateApiKeyRequest(BaseModel):
    api_key: str


def _require_admin(x_api_key: str | None):
    try:
        return get_client_from_api_key(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _read_ledger_entries():
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


def _normalize_case_ledger_entry(entry: dict) -> dict | None:
    data = entry.get("data", {})
    timestamp = entry.get("timestamp")
    ledger_hash = entry.get("hash")
    prev_hash = entry.get("prev_hash")

    event_type = data.get("event_type")

    # Nuovo formato: decisione engine ricca
    if event_type == "ENGINE_DECISION":
        return {
            "timestamp": timestamp,
            "event_type": "ENGINE_DECISION",
            "decision_id": data.get("decision_id"),
            "client_id": data.get("client_id"),
            "module": data.get("module"),
            "status": data.get("status"),
            "severity": data.get("severity"),
            "risk_score": data.get("risk_score"),
            "decision_code": data.get("decision_code"),
            "review_action": None,
            "reviewer_id": None,
            "reason": None,
            "ledger_hash": ledger_hash,
            "prev_hash": prev_hash,
            "source_format": "canonical",
        }

    # Nuovo formato: review umana
    if event_type == "HUMAN_REVIEW":
        return {
            "timestamp": timestamp,
            "event_type": "HUMAN_REVIEW",
            "decision_id": data.get("decision_id"),
            "client_id": data.get("client_id"),
            "module": data.get("module"),
            "status": data.get("review_action"),
            "severity": None,
            "risk_score": None,
            "decision_code": None,
            "review_action": data.get("review_action"),
            "reviewer_id": data.get("reviewer_id"),
            "reason": data.get("reason"),
            "ledger_hash": ledger_hash,
            "prev_hash": prev_hash,
            "source_format": "canonical",
        }

    # Legacy: decision payload ricco annidato in data["decision"]
    decision = data.get("decision")
    if isinstance(decision, dict):
        return {
            "timestamp": timestamp,
            "event_type": "LEGACY_ENGINE_DECISION",
            "decision_id": data.get("decision_id"),
            "client_id": data.get("client_id"),
            "module": data.get("module"),
            "status": decision.get("status"),
            "severity": decision.get("severity"),
            "risk_score": decision.get("risk_score"),
            "decision_code": decision.get("decision_code"),
            "review_action": None,
            "reviewer_id": None,
            "reason": None,
            "ledger_hash": ledger_hash,
            "prev_hash": prev_hash,
            "source_format": "legacy_dict",
        }

    # Legacy: decision semplice stringa
    if isinstance(decision, str):
        return {
            "timestamp": timestamp,
            "event_type": "LEGACY_ENGINE_DECISION",
            "decision_id": data.get("decision_id"),
            "client_id": data.get("client_id"),
            "module": data.get("module"),
            "status": decision,
            "severity": None,
            "risk_score": None,
            "decision_code": None,
            "review_action": None,
            "reviewer_id": None,
            "reason": None,
            "ledger_hash": ledger_hash,
            "prev_hash": prev_hash,
            "source_format": "legacy_string",
        }

    return None


@router.get("/admin/api-keys")
def get_api_keys():
    return list_api_keys()


@router.post("/admin/api-keys/revoke")
def revoke_api_key_endpoint(request: RevokeApiKeyRequest):
    revoked = revoke_api_key(request.api_key)

    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "status": "revoked",
        "api_key": request.api_key,
    }


@router.post("/admin/api-keys/rotate")
def rotate_api_key_endpoint(request: RotateApiKeyRequest):
    new_key = rotate_api_key(request.api_key)

    if not new_key:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "status": "rotated",
        "old_api_key": request.api_key,
        "new_api_key": new_key,
    }


@router.get("/admin/ledger/verify")
def verify_ledger(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    admin_client = _require_admin(x_api_key)

    ledger_ok = verify_chain()

    return {
        "requested_by": admin_client,
        "ledger_ok": ledger_ok,
    }


@router.get("/admin/ledger/raw")
def get_ledger_raw(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    admin_client = _require_admin(x_api_key)

    entries = _read_ledger_entries()

    return {
        "requested_by": admin_client,
        "entries_count": len(entries),
        "entries": entries,
    }


@router.get("/admin/ledger/by-case/{decision_id}")
def get_ledger_by_case(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    admin_client = _require_admin(x_api_key)

    entries = get_ledger_entries_by_decision_id(decision_id)

    normalized_entries = []
    for entry in entries:
        normalized = _normalize_case_ledger_entry(entry)
        if normalized:
            normalized_entries.append(normalized)

    if not normalized_entries:
        raise HTTPException(status_code=404, detail="Ledger entries not found for case")

    return {
        "requested_by": admin_client,
        "decision_id": decision_id,
        "entries_count": len(normalized_entries),
        "entries": normalized_entries,
    }
