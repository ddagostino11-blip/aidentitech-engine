from core.verify_ledger import verify_ledger
from core.verify_ledger_signature import main as verify_signature
from cli.run_validation import run_validation


def execute_validation(config: dict, module_config: dict, module_name: str, payload: dict | None = None):
    # Per ora il payload viene accettato e passato come contesto futuro.
    # La pipeline reale continua a usare config + module_config.
    run_validation(
        config,
        module_config,
        verify_ledger,
        verify_signature
    )

    return {
        "status": "completed",
        "module": module_name,
        "payload_received": payload or {}
    }
