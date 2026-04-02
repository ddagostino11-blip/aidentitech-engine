from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import importlib

from core.config_loader import load_config
from services.validation_service import execute_validation

app = FastAPI(title="Aidentitech Engine API")


# =========================
# REQUEST MODEL
# =========================
class ValidateRequest(BaseModel):
    module: str
    payload: dict | None = None


# =========================
# MODULE LOADER
# =========================
def load_module_config(module_name: str):
    try:
        module = importlib.import_module(f"modules.{module_name}.config")
        return getattr(module, f"get_{module_name}_config")()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Modulo non valido: {module_name}"
        )


# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"status": "engine running"}


# =========================
# STATUS
# =========================
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


# =========================
# VALIDATE (CON PAYLOAD)
# =========================
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

    return {
        "engine": "aidentitech",
        "module": request.module,
        "result": result
    }
