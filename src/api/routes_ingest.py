from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from src.core.auth import get_client_from_api_key
from src.core.payload_adapter import normalize_payload
from src.modules.registry import AVAILABLE_MODULES
from src.core.module_router import run_module
from src.core.db import insert_case
from core.ledger_chain import append_ledger_entry

from datetime import datetime, timezone
import uuid
import importlib

router = APIRouter(tags=["ingest"])


class IngestPharmaRequest(BaseModel):
    payload: dict


def load_module_config(module_name: str):
    try:
        module = importlib.import_module(f"src.modules.{module_name}.config")
        return module.load_config()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Modulo non valido: {module_name}"
        )


@router.post("/ingest/pharma")
def ingest_pharma(
    request: IngestPharmaRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    try:
        client_id = get_client_from_api_key(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    module_name = "pharma"

    if module_name not in AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail="Modulo pharma non disponibile")

    if not AVAILABLE_MODULES[module_name]["enabled"]:
        raise HTTPException(status_code=400, detail="Modulo pharma disabilitato")

    try:
        module_config = load_module_config(module_name)

        raw_payload = request.payload or {}
        payload = normalize_payload(raw_payload)

        # =========================
        # INTEGRATION CONTEXT
        # =========================
        context = raw_payload.get("context", {}) if isinstance(raw_payload, dict) else {}

        source_system = context.get("source_system", "unknown")
        site = context.get("site", "unknown")
        line = context.get("line", None)

        ingestion_timestamp = datetime.now(timezone.utc).isoformat()

        required_fields = [
            "product_id",
            "batch",
            "gmp_compliant",
            "temperature",
        ]

        missing_fields = [
            field for field in required_fields
            if field not in payload or payload.get(field) is None
        ]

        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required payload fields for pharma: {', '.join(missing_fields)}"
            )

        decision = run_module(
            module_name,
            module_config,
            payload
        )

        decision_id = str(uuid.uuid4())
        decision_timestamp = datetime.now(timezone.utc).isoformat()

        ledger_entry = append_ledger_entry({
            "client_id": client_id,
            "module": module_name,
            "decision": decision.get("status"),
            "decision_id": decision_id,
        })

        response = {
            "engine": "Aidentitech",
            "entrypoint": "ingest_pharma",
            "module": module_name,
            "client_id": client_id,
            "status": decision.get("status"),
            "severity": decision.get("severity"),
            "risk_score": decision.get("risk_score"),
            "recommended_action": decision.get("recommended_action"),
            "decision_code": decision.get("decision_code"),
            "review_required": decision.get("review_required"),
            "blocking_issues_count": decision.get("blocking_issues_count"),
            "regulatory_impact": decision.get("regulatory_impact"),
            "batch_disposition": decision.get("batch_disposition"),
            "issues": decision.get("issues", []),
            "audit": decision.get("audit", []),
            "explanation": decision.get("explanation", {}),
            "decision_id": decision_id,
            "decision_timestamp": decision_timestamp,
            "policy_profile": decision.get("policy_profile"),
            "versioning": module_config.get("versioning", {}),
            "compliance_scope": decision.get("compliance_scope", {}),
            "ledger_hash": ledger_entry.get("hash"),
            "payload_received": raw_payload,
            "normalized_payload": payload,
            "integration": {
                "source_system": source_system,
                "site": site,
                "line": line,
                "ingestion_timestamp": ingestion_timestamp
            },
        }

        insert_case({
            "decision_id": decision_id,
            "client_id": client_id,
            "module": module_name,
            "status": decision.get("status"),
            "severity": decision.get("severity"),
            "risk_score": decision.get("risk_score"),
            "decision_code": decision.get("decision_code"),
            "payload": payload,
            "full_response": response,
        })

        return response

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingest error: {str(e)}"
        )
