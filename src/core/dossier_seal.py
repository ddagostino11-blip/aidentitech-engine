import hashlib
import json


def build_dossier_payload(case: dict) -> dict:
    return {
        "engine": case.get("engine"),
        "decision_id": case.get("decision_id"),
        "decision_timestamp": case.get("decision_timestamp"),
        "client_id": case.get("client_id"),
        "module": case.get("module"),
        "decision": {
            "status": case.get("status"),
            "severity": case.get("severity"),
            "risk_score": case.get("risk_score"),
            "decision_code": case.get("decision_code"),
            "recommended_action": case.get("recommended_action"),
            "batch_disposition": case.get("batch_disposition"),
        },
        "audit": case.get("audit", []),
        "explanation": case.get("explanation", {}),
        "integration": case.get("integration", {}),
        "payload": case.get("normalized_payload", {}),
        "versioning": case.get("versioning", {}),
        "compliance_scope": case.get("compliance_scope", {}),
        "ledger_hash": case.get("ledger_hash"),
    }


def compute_dossier_hash(dossier: dict) -> str:
    canonical = json.dumps(dossier, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
