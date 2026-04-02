import importlib

from core.verify_ledger import verify_ledger
from core.verify_ledger_signature import main as verify_signature
from cli.run_validation import run_validation as base_run_validation


def execute_validation(config: dict, module_config: dict, module_name: str, payload: dict | None = None):
    base_run_validation(
        config,
        module_config,
        verify_ledger,
        verify_signature
    )

    payload = payload or {}

    try:
        module_path = f"src.modules.{module_name}.logic"
        logic = importlib.import_module(module_path)
        decision = logic.run(module_config, payload)

    except ModuleNotFoundError:
        decision = {
            "status": "ERROR",
            "severity": "HIGH",
            "risk_score": 100,
            "issues": [f"module_logic_not_found:{module_name}"],
            "recommended_action": "CHECK_MODULE_IMPLEMENTATION"
        }

    return {
        "module": module_name,
        "decision": decision,
        "payload_received": payload
    }
