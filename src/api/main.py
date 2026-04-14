from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, model_validator
from datetime import datetime, timezone
import uuid
import importlib

from core.config_loader import load_config
from core.ledger_chain import append_ledger_entry
from src.modules.registry import AVAILABLE_MODULES
from src.core.module_router import run_module

# DB
from src.core.db import init_db, insert_case

# auth
from src.core.auth import get_client_from_api_key

# payload adapter
from src.core.payload_adapter import normalize_payload

# dossier seal
from src.core.dossier_seal import build_dossier_payload, compute_dossier_hash

# routes
from src.api.routes_cases import router as cases_router
from src.api.routes_admin import router as admin_router
from src.api.routes_ingest import router as ingest_router

ENGINE_NAME = "Aidentitech"

app = FastAPI(title=f"{ENGINE_NAME} Engine API")


# init DB all’avvio
@app.on_event("startup")
def startup_event():
    init_db()


# endpoint routes
app.include_router(cases_router)
app.include_router(admin_router)
app.include_router(ingest_router)


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
    except ValueError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payload validation error for module {module_name}: {str(e)}"
        )


class ValidateRequest(BaseModel):
    module: str
    payload: dict | None = None
    client_id: str | None = "anonymous"

    @model_validator(mode="after")
    def validate_payload_for_module(self):
        raw_payload = self.payload or {}
        payload = normalize_payload(raw_payload)

        try:
            validate_module_payload(self.module, payload)
        except HTTPException:
            raise
        except ValueError as e:
            raise ValueError(str(e))

        return self


@app.get("/")
def root():
    return {"status": f"{ENGINE_NAME} running"}


@app.get("/status")
def status(module: str = "pharma"):
    config = load_config()
    module_config = load_module_config(module)

    return {
        "engine": ENGINE_NAME,
        "module": module,
        "status": "ready",
        "config_loaded": bool(config),
        "module_loaded": bool(module_config)
    }


@app.post("/validate")
def validate(
    request: ValidateRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    try:
        client_id = get_client_from_api_key(x_api_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if request.module not in AVAILABLE_MODULES:
        raise HTTPException(
            status_code=400,
            detail=f"Modulo non valido: {request.module}"
        )

    if not AVAILABLE_MODULES[request.module]["enabled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Modulo disabilitato: {request.module}"
        )

    try:
        module_config = load_module_config(request.module)

        raw_payload = request.payload or {}
        payload = normalize_payload(raw_payload)

        validate_module_payload(request.module, payload)

        # run engine
        decision = run_module(
            request.module,
            module_config,
            payload
        )

        decision_id = str(uuid.uuid4())
        decision_timestamp = datetime.now(timezone.utc).isoformat()

        # ledger
        ledger_entry = append_ledger_entry({
            "client_id": client_id,
            "module": request.module,
            "decision": decision.get("status"),
            "decision_id": decision_id,
        })

        # response finale
        response = {
            "engine": ENGINE_NAME,
            "module": request.module,
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
        }

        # dossier + hash
        dossier_source = build_dossier_payload(response)
        dossier_hash = compute_dossier_hash(dossier_source)
        response["dossier_hash"] = dossier_hash

        # salvataggio DB
        insert_case({
            "decision_id": decision_id,
            "client_id": client_id,
            "module": request.module,
            "status": decision.get("status"),
            "severity": decision.get("severity"),
            "risk_score": decision.get("risk_score"),
            "decision_code": decision.get("decision_code"),
            "payload": payload,
            "full_response": response,
            "dossier_hash": dossier_hash,
        })

        return response

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation error: {str(e)}"
        )
