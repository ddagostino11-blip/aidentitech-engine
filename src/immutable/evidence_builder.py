from datetime import datetime
from typing import Dict, Any

from src.immutable.hash_service import build_hash_record


def build_decision_evidence(
    *,
    module: str,
    payload: Dict[str, Any],
    decision_result: Dict[str, Any]
) -> Dict[str, Any]:
    evidence_payload = {
        "evidence_type": "decision",
        "module": module,
        "created_at": datetime.utcnow().isoformat(),
        "payload_received": payload,
        "decision_result": decision_result
    }

    return build_hash_record("decision_evidence", evidence_payload)


def build_regulatory_delta_evidence(delta: Dict[str, Any]) -> Dict[str, Any]:
    evidence_payload = {
        "evidence_type": "regulatory_delta",
        "created_at": datetime.utcnow().isoformat(),
        "delta": delta
    }

    return build_hash_record("regulatory_delta_evidence", evidence_payload)


def build_rule_version_evidence(versioning_result: Dict[str, Any]) -> Dict[str, Any]:
    evidence_payload = {
        "evidence_type": "rule_version",
        "created_at": datetime.utcnow().isoformat(),
        "versioning_result": versioning_result
    }

    return build_hash_record("rule_version_evidence", evidence_payload)


def build_client_alert_evidence(alert: Dict[str, Any]) -> Dict[str, Any]:
    evidence_payload = {
        "evidence_type": "client_alert",
        "created_at": datetime.utcnow().isoformat(),
        "alert": alert
    }

    return build_hash_record("client_alert_evidence", evidence_payload)
