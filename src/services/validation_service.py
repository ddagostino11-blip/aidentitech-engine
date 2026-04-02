from cli.run_validation import run_validation
from core.verify_ledger import verify_ledger
from core.verify_ledger_signature import main as verify_signature
from core.config_loader import load_config


def execute_validation(module_config: dict):
    config = load_config()

    run_validation(
        config,
        module_config,
        verify_ledger,
        verify_signature
    )

    return {
        "status": "completed",
        "module": module_config["module_name"]
    }
