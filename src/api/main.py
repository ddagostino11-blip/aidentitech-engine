from typing import Optional, List
import importlib

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator

from core.config_loader import load_config
from services.validation_service import execute_validation
from core.ledger_chain import append_ledger_entry
from src.modules.registry import AVAILABLE_MODULES
from src.orchestrator.pipeline import run_validation_pipeline
from src.sentinel.legal_decision_handler import (
    handle_legal_decision,
    handle_legal_reopen,
)
from src.services.event_store import load_event_store, get_event_audit
from src.services.event_query import filter_events

app = FastAPI(title="Aidentitech Engine API")


class ValidateRequest(BaseModel):
    client_id: str
    product_id: str
    module: str
    payload: dict
    frameworks: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_payload_for_module(self):
        if self.module == "pharma":
            payload = self.payload or {}

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
                raise ValueError(
                    f"Missing required payload fields for pharma: {', '.join(missing_fields)}"
                )

        return self


class LegalDecisionRequest(BaseModel):
    event_id: str
    decision: str
    reviewer_name: Optional[str] = "LEGAL_TEAM"
    notes: Optional[str] = None


class LegalReopenRequest(BaseModel):
    event_id: str
    reviewer_name: Optional[str] = "LEGAL_TEAM"
    notes: Optional[str] = None


def load_module_config(module_name: str):
    try:
        module = importlib.import_module(f"src.modules.{module_name}.config")
        return module.load_config()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Modulo non valido: {module_name}"
        )


@app.get("/")
def root():
    return {"status": "engine running"}


@app.get("/status")
def status(module: str = "pharma"):
    config = load_config()
    module_config = load_module_config(module)

    return {
        "engine": "aidentitech",
        "module": module,
        "status": "ready",
        "config_loaded": bool(config),
        "module_loaded": bool(module_config)
    }


@app.post("/validate")
def validate(request: ValidateRequest):
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
        return run_validation_pipeline(
            client_id=request.client_id,
            product_id=request.product_id,
            module=request.module,
            payload=request.payload,
            frameworks=request.frameworks or [],
            load_config_fn=load_config,
            load_module_config_fn=load_module_config,
            execute_validation_fn=execute_validation,
            append_ledger_entry_fn=append_ledger_entry,
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation error: {str(e)}"
        )


@app.get("/legal/events")
def get_legal_events(
    status: Optional[str] = None,
    domain: Optional[str] = None,
    client_id: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    sort_by: Optional[str] = "created_at",
    order: Optional[str] = "desc",
):
    try:
        store = load_event_store()
        events = store.get("events", [])

        filtered_all = filter_events(
            events=events,
            status=status,
            domain=domain,
            client_id=client_id,
            product_id=product_id,
            limit=None,
            offset=0,
            sort_by=sort_by,
            order=order,
        )

        paged = filter_events(
            events=events,
            status=status,
            domain=domain,
            client_id=client_id,
            product_id=product_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order,
        )

        return {
            "count": len(filtered_all),
            "events": paged
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Legal events error: {str(e)}"
        )


@app.get("/legal/events/{event_id}/audit")
def get_legal_events_audit(event_id: str):
    try:
        audit = get_event_audit(event_id)

        if audit is None:
            raise HTTPException(
                status_code=404,
                detail="event_not_found"
            )

        return {
            "event_id": event_id,
            "steps": audit
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Audit error: {str(e)}"
        )


@app.post("/legal/decision")
def legal_decision(request: LegalDecisionRequest):
    try:
        result = handle_legal_decision(
            event_id=request.event_id,
            decision=request.decision,
            reviewer_name=request.reviewer_name or "LEGAL_TEAM",
            notes=request.notes
        )

        if result.get("error") == "event_not_found":
            raise HTTPException(status_code=404, detail="event_not_found")

        if result.get("error") == "invalid_state":
            raise HTTPException(status_code=400, detail=result)

        if result.get("error") == "invalid_decision":
            raise HTTPException(status_code=400, detail="invalid_decision")

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Legal decision error: {str(e)}"
        )


@app.post("/legal/reopen")
def legal_reopen(request: LegalReopenRequest):
    try:
        result = handle_legal_reopen(
            event_id=request.event_id,
            reviewer_name=request.reviewer_name or "LEGAL_TEAM",
            notes=request.notes
        )

        if result.get("error") == "event_not_found":
            raise HTTPException(status_code=404, detail="event_not_found")

        if result.get("error") == "invalid_state":
            raise HTTPException(status_code=400, detail=result)

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Legal reopen error: {str(e)}"
        )
