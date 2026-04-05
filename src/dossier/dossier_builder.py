from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from src.immutable.evidence_builder import build_decision_evidence


def build_precompliance_dossier(
    *,
    module: str,
    jurisdiction: str,
    payload: Dict[str, Any],
    decision_result: Dict[str, Any],
    regulatory_context: Optional[Dict[str, Any]] = None,
    immutable_evidence: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Costruisce il dossier strutturato di pre-compliance.
    Questo è il documento canonico da cui in futuro potrai:
    - archiviare JSON
    - generare PDF
    - inviare al cliente
    - registrare su ledger
    """

    if immutable_evidence is None:
        immutable_evidence = build_decision_evidence(
            module=module,
            payload=payload,
            decision_result=decision_result
        )

    dossier = {
        "dossier_id": str(uuid4()),
        "dossier_type": "PRECOMPLIANCE",
        "module": module,
        "jurisdiction": jurisdiction,
        "generated_at": datetime.utcnow().isoformat(),

        "payload_received": payload,

        "decision": {
            "status": decision_result.get("status"),
            "severity": decision_result.get("severity"),
            "risk_score": decision_result.get("risk_score"),
            "recommended_action": decision_result.get("recommended_action"),
            "issues": decision_result.get("issues", []),
            "audit": decision_result.get("audit", []),
            "explanation": decision_result.get("explanation", {})
        },

        "regulatory_context": regulatory_context or {
            "delta_detected": False,
            "delta_reference": None,
            "rule_version_reference": None
        },

        "immutable_evidence": {
            "record_type": immutable_evidence.get("record_type"),
            "sha256": immutable_evidence.get("sha256"),
            "canonical_payload": immutable_evidence.get("canonical_payload")
        }
    }

    return dossier
