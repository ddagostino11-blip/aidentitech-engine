import hashlib
import json
import os
import hmac


def build_dossier_payload(case: dict) -> dict:
    return {
        "engine": case.get("engine"),
        "dossier_type": case.get("dossier_type"),
        "decision_id": case.get("decision_id"),
        "decision_timestamp": case.get("decision_timestamp"),
        "client_id": case.get("client_id"),
        "module": case.get("module"),
        "engine_status": case.get("engine_status"),
        "final_status": case.get("final_status"),
        "has_human_review": case.get("has_human_review"),
        "has_admin_override": case.get("has_admin_override"),
        "latest_review_action": case.get("latest_review_action"),
        "review_count": case.get("review_count"),
        "override_count": case.get("override_count"),
        "latest_event_timestamp": case.get("latest_event_timestamp"),
        "events_count": case.get("events_count"),
        "latest_ledger_hash": case.get("latest_ledger_hash"),
        "decision": {
            "status": case.get("status"),
            "severity": case.get("severity"),
            "risk_score": case.get("risk_score"),
            "decision_code": case.get("decision_code"),
            "recommended_action": case.get("recommended_action"),
            "batch_disposition": case.get("batch_disposition"),
        },
        "timeline": case.get("timeline", []),
        "audit": case.get("audit", []),
        "explanation": case.get("explanation", {}),
        "integration": case.get("integration", {}),
        "payload": case.get("normalized_payload", {}),
        "versioning": case.get("versioning", {}),
        "compliance_scope": case.get("compliance_scope", {}),
        "ledger_hash": case.get("ledger_hash"),
        "proof": {
            "ledger_hash": case.get("ledger_hash"),
            "checkpoint_hash": case.get("checkpoint_hash"),
            "anchor_sha256": case.get("anchor_sha256"),
            "anchor_external_path": case.get("anchor_external_path"),
            "timestamp_status": case.get("timestamp_status"),
            "timestamp_provider": case.get("timestamp_provider"),
            "timestamp_proof": case.get("timestamp_proof"),
        },
    }


def _canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def compute_dossier_hash(dossier: dict) -> str:
    canonical = _canonical_json(dossier)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_dossier_signature(dossier: dict) -> str:
    """
    Firma HMAC SHA256 del dossier.
    Usa una secret lato server.
    """
    secret = os.getenv("DOSSIER_SIGNING_SECRET", "dev-secret-change-me")

    canonical = _canonical_json(dossier)

    signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=canonical.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return signature
