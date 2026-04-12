from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator
import importlib

from core.config_loader import load_config
from services.validation_service import execute_validation
from core.ledger_chain import append_ledger_entry
from src.modules.registry import AVAILABLE_MODULES

# 🔧 Centralized constant
ENGINE_NAME = "Aidentitech"

app = FastAPI(title=f"{ENGINE_NAME} Engine API")


class ValidateRequest(BaseModel):
    module: str
    payload: dict | None = None
    client_id: str | None = "anonymous"

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

        result = execute_validation(
            config=config,
            module_config=module_config,
            module_name=request.module,
            payload=request.payload
        )

        decision = result.get("decision", {})

        ledger_entry = append_ledger_entry({
            "client_id": request.client_id,
            "module": request.module,
            "decision": decision.get("status"),
        })

        return {
            "engine": ENGINE_NAME,
            "module": request.module,
            "client_id": request.client_id,

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
