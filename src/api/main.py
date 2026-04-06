from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator
import importlib

from core.config_loader import load_config
from services.validation_service import execute_validation
from core.ledger_chain import append_ledger_entry

app = FastAPI(title="Aidentitech Engine API")


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
    config = load_config()
    module_config = load_module_config(request.module)

    result = execute_validation(
        config=config,
        module_config=module_config,
        module_name=request.module,
        payload=request.payload
    )

    ledger_entry = append_ledger_entry({
        "client_id": request.client_id,
        "module": request.module,
        "decision": result.get("decision"),
    })

    return {
        "engine": "aidentitech",
        "module": request.module,
        "client_id": request.client_id,
        "result": result,
        "ledger_hash": ledger_entry["hash"]
    }
