from typing import Optional, List
import importlib

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator

from core.config_loader import load_config
from services.validation_service import execute_validation
from core.ledger_chain import append_ledger_entry
from src.modules.registry import AVAILABLE_MODULES
from src.sentinel.legal_decision_handler import handle_legal_decision
from src.services.event_store import filter_events

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
        config = load_config()
        module_config = load_module_config(request.module)

        frameworks = request.frameworks or []
        module_config["selected_frameworks"] = frameworks

        result = execute_validation(
            config=config,
            module_config=module_config,
            module_name=request.module,
            payload=request.payload
        )

        decision = result.get("decision", {})

        ledger_entry = append_ledger_entry({
            "client_id": request.client_id,
            "product_id": request.product_id,
            "module": request.module,
            "decision": decision.get("status"),
        })

        return {
            "engine": "aidentitech",
            "module": request.module,
            "client_id": request.client_id,
            "product_id": request.product_id,
            "decision_trace_id": ledger_entry.get("hash"),
            "output_type": decision.get("output_type"),
            "execution_allowed": decision.get("execution_allowed"),
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
            "payload_received": result.get("payload_received", {}),
            "versioning": result.get("versioning", module_config.get("versioning", {})),
            "compliance_scope": decision.get("compliance_scope", {}),
            "ledger_hash": ledger_entry.get("hash"),
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation error: {str(e)}"
        )


@app.get("/legal/events")
def get_legal_events(status: Optional[str] = None, domain: Optional[str] = None):
    try:
        events = filter_events(status=status, domain=domain)

        return {
            "count": len(events),
            "events": events
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Legal events error: {str(e)}"
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
