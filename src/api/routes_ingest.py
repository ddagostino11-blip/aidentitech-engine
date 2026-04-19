from datetime import datetime, timezone
import importlib
import json
import os
import uuid
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from src.core.auth import get_client_from_api_key
from src.core.payload_adapter import normalize_payload
from src.modules.registry import AVAILABLE_MODULES
from src.core.module_router import run_module
from src.core.db import insert_case
from src.core.dossier_seal import (
    build_dossier_payload,
    compute_dossier_hash,
    compute_dossier_signature,
)
from src.core.ledger_chain import append_ledger_entry, build_canonical_ledger_data

router = APIRouter(tags=["ingest"])


WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_TIMEOUT_SECONDS = float(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "3.0"))


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


def validate_module_payload(module_name: str, payload: dict | None):
    try:
        validator_module = importlib.import_module(
            f"src.modules.{module_name}.validator"
        )
        validate_fn = getattr(validator_module, "validate_payload", None)

        if callable(validate_fn):
            validate_fn(payload)

    except ModuleNotFoundError:
        return
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payload validation error for module {module_name}: {str(e)}"
        )


def send_webhook_event(event_payload: dict) -> dict | None:
    if not WEBHOOK_URL:
        return None

    body = json.dumps(event_payload).encode("utf-8")

    req = urllib_request.Request(
        WEBHOOK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Aidentitech-Webhook/1.0",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=WEBHOOK_TIMEOUT_SECONDS) as resp:
            return {
                "delivered": True,
                "status_code": resp.getcode(),
            }
    except HTTPError as e:
        return {
            "delivered": False,
            "status_code": e.code,
            "error": str(e),
        }
    except URLError as e:
        return {
            "delivered": False,
            "status_code": None,
            "error": str(e),
        }
    except Exception as e:
        return {
            "delivered": False,
            "status_code": None,
            "error": str(e),
        }


@router.post("/ingest/pharma")
def ingest_pharma(
    request: IngestPharmaRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    try:
        auth = get_client_from_api_key(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    client_id = auth.get("client_id")
    if not client_id:
        raise HTTPException(status_code=401, detail="Invalid client authentication")

    module_name = "pharma"

    if module_name not in AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail="Modulo pharma non disponibile")

    if not AVAILABLE_MODULES[module_name]["enabled"]:
        raise HTTPException(status_code=400, detail="Modulo pharma disabilitato")

    try:
        module_config = load_module_config(module_name)

        raw_payload = request.payload or {}
        payload = normalize_payload(raw_payload)

        validate_module_payload(module_name, payload)

        context = raw_payload.get("context", {}) if isinstance(raw_payload, dict) else {}

        source_system = context.get("source_system", "unknown")
        site = context.get("site", "unknown")
        line = context.get("line")

        ingestion_timestamp = datetime.now(timezone.utc).isoformat()

        decision = run_module(
            module_name,
            module_config,
            payload
        )

        decision_id = str(uuid.uuid4())
        decision_timestamp = datetime.now(timezone.utc).isoformat()

        ledger_entry = append_ledger_entry(
            build_canonical_ledger_data(
                event_type="ENGINE_DECISION",
                decision_id=decision_id,
                client_id=client_id,
                module=module_name,
                status=decision.get("status"),
                severity=decision.get("severity"),
                risk_score=decision.get("risk_score"),
                decision_code=decision.get("decision_code"),
                metadata={},
            )
        )

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
            "ledger_event_id": ledger_entry.get("event_id"),
            "payload_received": raw_payload,
            "normalized_payload": payload,
            "integration": {
                "source_system": source_system,
                "site": site,
                "line": line,
                "ingestion_timestamp": ingestion_timestamp,
            },
        }

        dossier_source = build_dossier_payload(response)
        dossier_hash = compute_dossier_hash(dossier_source)
        dossier_signature = compute_dossier_signature(dossier_source)

        response["dossier_hash"] = dossier_hash
        response["signature"] = dossier_signature

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
            "dossier_hash": dossier_hash,
            "signature": dossier_signature,
        })

        webhook_payload = {
            "event_type": "ENGINE_DECISION",
            "engine": "Aidentitech",
            "decision_id": decision_id,
            "client_id": client_id,
            "module": module_name,
            "engine_status": decision.get("status"),
            "final_status": decision.get("status"),
            "severity": decision.get("severity"),
            "risk_score": decision.get("risk_score"),
            "decision_code": decision.get("decision_code"),
            "recommended_action": decision.get("recommended_action"),
            "batch_disposition": decision.get("batch_disposition"),
            "decision_timestamp": decision_timestamp,
            "ledger_hash": ledger_entry.get("hash"),
            "ledger_event_id": ledger_entry.get("event_id"),
            "dossier_hash": dossier_hash,
            "signature": dossier_signature,
            "integration": {
                "source_system": source_system,
                "site": site,
                "line": line,
                "ingestion_timestamp": ingestion_timestamp,
            },
        }

        webhook_result = send_webhook_event(webhook_payload)
        response["webhook"] = webhook_result or {
            "delivered": False,
            "status_code": None,
            "error": "WEBHOOK_URL not configured",
        }

        return response

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingest error: {str(e)}"
        )
