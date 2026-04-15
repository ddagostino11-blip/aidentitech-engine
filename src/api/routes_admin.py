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

CANONICAL_EVENT_TYPES = {"ENGINE_DECISION", "HUMAN_REVIEW"}
ENGINE_EVENT_TYPES = {"ENGINE_DECISION", "LEGACY_ENGINE_DECISION"}
REVIEW_EVENT_TYPES = {"HUMAN_REVIEW"}


class RevokeApiKeyRequest(BaseModel):
    api_key: str


class RotateApiKeyRequest(BaseModel):
    api_key: str


def _require_admin_scope(x_api_key: str | None):
    try:
        auth = get_client_from_api_key(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    role = auth.get("role")

    if role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")

    return auth


def _require_super_admin(x_api_key: str | None):
    auth = _require_admin_scope(x_api_key)

    if auth.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")

    return auth


def _is_super_admin(auth: dict) -> bool:
    return auth.get("role") == "super_admin"


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


def _entry_belongs_to_auth(entry: dict, auth: dict) -> bool:
    if _is_super_admin(auth):
        return True

    data = entry.get("data", {})
    return data.get("client_id") == auth.get("client_id")


def _filter_entries_for_auth(entries: list[dict], auth: dict) -> list[dict]:
    if _is_super_admin(auth):
        return entries

    return [entry for entry in entries if _entry_belongs_to_auth(entry, auth)]


def _base_normalized_entry(entry: dict) -> dict:
    data = entry.get("data", {})

    return {
        "timestamp": entry.get("timestamp"),
        "event_type": None,
        "decision_id": data.get("decision_id"),
        "client_id": data.get("client_id"),
        "module": data.get("module"),
        "status": None,
        "severity": None,
        "risk_score": None,
        "decision_code": None,
        "review_action": None,
        "reviewer_id": None,
        "reason": None,
        "ledger_hash": entry.get("hash"),
        "prev_hash": entry.get("prev_hash"),
        "source_format": "unknown",
        "raw_event_type": data.get("event_type"),
    }


def _normalize_canonical_entry(entry: dict) -> dict | None:
    data = entry.get("data", {})
    event_type = data.get("event_type")

    if event_type not in CANONICAL_EVENT_TYPES:
        return None

    normalized = _base_normalized_entry(entry)

    if event_type == "ENGINE_DECISION":
        normalized.update({
            "event_type": "ENGINE_DECISION",
            "status": data.get("status"),
            "severity": data.get("severity"),
            "risk_score": data.get("risk_score"),
            "decision_code": data.get("decision_code"),
            "source_format": "canonical",
        })
        return normalized

    if event_type == "HUMAN_REVIEW":
        normalized.update({
            "event_type": "HUMAN_REVIEW",
            "status": data.get("review_action") or data.get("status"),
            "review_action": data.get("review_action"),
            "reviewer_id": data.get("reviewer_id"),
            "reason": data.get("reason"),
            "source_format": "canonical",
        })
        return normalized

    return None


def _normalize_legacy_entry(entry: dict) -> dict | None:
    data = entry.get("data", {})
    decision = data.get("decision")

    normalized = _base_normalized_entry(entry)

    if isinstance(decision, dict):
        normalized.update({
            "event_type": "LEGACY_ENGINE_DECISION",
            "status": decision.get("status"),
            "severity": decision.get("severity"),
            "risk_score": decision.get("risk_score"),
            "decision_code": decision.get("decision_code"),
            "source_format": "legacy_dict",
        })
        return normalized

    if isinstance(decision, str):
        normalized.update({
            "event_type": "LEGACY_ENGINE_DECISION",
            "status": decision,
            "source_format": "legacy_string",
        })
        return normalized

    # caso legacy incompleto o ambiguo: non lo buttiamo via
    if any(
        key in data
        for key in ["client_id", "module", "decision_id", "status", "severity", "risk_score"]
    ):
        normalized.update({
            "event_type": "LEGACY_UNKNOWN",
            "status": data.get("status"),
            "severity": data.get("severity"),
            "risk_score": data.get("risk_score"),
            "decision_code": data.get("decision_code"),
            "source_format": "legacy_unknown",
        })
        return normalized

    return None


def _normalize_case_ledger_entry(entry: dict) -> dict | None:
    return _normalize_canonical_entry(entry) or _normalize_legacy_entry(entry)


def _normalize_entries(entries: list[dict]) -> list[dict]:
    normalized_entries = []

    for entry in entries:
        normalized = _normalize_case_ledger_entry(entry)
        if normalized:
            normalized_entries.append(normalized)

    return normalized_entries


def _build_ledger_summary(normalized_entries: list[dict], decision_id: str) -> dict:
    if not normalized_entries:
        raise HTTPException(status_code=404, detail="Ledger entries not found for case")

    ordered = sorted(normalized_entries, key=lambda e: e.get("timestamp") or "")

    engine_entries = [
        e for e in ordered
        if e.get("event_type") in ENGINE_EVENT_TYPES
    ]
    review_entries = [
        e for e in ordered
        if e.get("event_type") in REVIEW_EVENT_TYPES
    ]

    latest_engine = engine_entries[-1] if engine_entries else None
    latest_review = review_entries[-1] if review_entries else None
    latest_event = ordered[-1]

    engine_status = latest_engine.get("status") if latest_engine else None
    latest_review_action = latest_review.get("review_action") if latest_review else None
    final_status = latest_review_action or engine_status or latest_event.get("status")

    base_entry = latest_review or latest_engine or latest_event

    return {
        "decision_id": decision_id,
        "client_id": base_entry.get("client_id"),
        "module": base_entry.get("module"),
        "engine_status": engine_status,
        "final_status": final_status,
        "has_human_review": len(review_entries) > 0,
        "latest_review_action": latest_review_action,
        "review_count": len(review_entries),
        "events_count": len(ordered),
        "latest_event_type": latest_event.get("event_type"),
        "latest_event_timestamp": latest_event.get("timestamp"),
        "latest_ledger_hash": latest_event.get("ledger_hash"),
        "latest_source_format": latest_event.get("source_format"),
    }


@router.get("/admin/api-keys")
def get_api_keys(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    auth = _require_super_admin(x_api_key)

    return {
        "requested_by": auth.get("client_id"),
        "requested_role": auth.get("role"),
        "items": list_api_keys(),
    }


@router.post("/admin/api-keys/revoke")
def revoke_api_key_endpoint(
    request: RevokeApiKeyRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    auth = _require_super_admin(x_api_key)

    revoked = revoke_api_key(request.api_key)

    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "requested_by": auth.get("client_id"),
        "requested_role": auth.get("role"),
        "status": "revoked",
        "api_key": request.api_key,
    }


@router.post("/admin/api-keys/rotate")
def rotate_api_key_endpoint(
    request: RotateApiKeyRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    auth = _require_super_admin(x_api_key)

    new_key = rotate_api_key(request.api_key)

    if not new_key:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "requested_by": auth.get("client_id"),
        "requested_role": auth.get("role"),
        "status": "rotated",
        "old_api_key": request.api_key,
        "new_api_key": new_key,
    }


@router.get("/admin/ledger/verify")
def verify_ledger(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    auth = _require_admin_scope(x_api_key)

    ledger_ok = verify_chain()

    return {
        "requested_by": auth.get("client_id"),
        "requested_role": auth.get("role"),
        "ledger_ok": ledger_ok,
    }


@router.get("/admin/ledger/raw")
def get_ledger_raw(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    auth = _require_admin_scope(x_api_key)

    entries = _read_ledger_entries()
    scoped_entries = _filter_entries_for_auth(entries, auth)

    return {
        "requested_by": auth.get("client_id"),
        "requested_role": auth.get("role"),
        "entries_count": len(scoped_entries),
        "entries": scoped_entries,
    }


@router.get("/admin/ledger/by-case/{decision_id}")
def get_ledger_by_case(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    auth = _require_admin_scope(x_api_key)

    entries = get_ledger_entries_by_decision_id(decision_id)
    scoped_entries = _filter_entries_for_auth(entries, auth)
    normalized_entries = _normalize_entries(scoped_entries)

    if not normalized_entries:
        raise HTTPException(status_code=404, detail="Ledger entries not found for case")

    return {
        "requested_by": auth.get("client_id"),
        "requested_role": auth.get("role"),
        "decision_id": decision_id,
        "entries_count": len(normalized_entries),
        "entries": normalized_entries,
    }


@router.get("/admin/ledger/summary/{decision_id}")
def get_ledger_summary(
    decision_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    auth = _require_admin_scope(x_api_key)

    entries = get_ledger_entries_by_decision_id(decision_id)
    scoped_entries = _filter_entries_for_auth(entries, auth)
    normalized_entries = _normalize_entries(scoped_entries)
    summary = _build_ledger_summary(normalized_entries, decision_id)

    return {
        "requested_by": auth.get("client_id"),
        "requested_role": auth.get("role"),
        **summary,
    }
