import sys

from src.cli.run_validation import main as run_validation
from src.core.verify_ledger import verify_ledger
from src.core.verify_ledger_signature import main as verify_signature
from src.core.config_loader import load_config


def main():
    config = load_config()

    if len(sys.argv) < 2:
        print("Uso: python3 run.py [validate | verify | status]")
        return

    command = sys.argv[1]

    if command == "validate":
        run_validation()

    elif command == "verify":
        print("=== VERIFY ===")
        ledger_ok = verify_ledger(config["paths"]["ledger_file"])
        signature_ok = verify_signature()

        if ledger_ok and signature_ok:
            print("✅ Sistema verificato OK")
        else:
            print("❌ Problema nella verifica")

    elif command == "status":
        print("=== STATUS ===")
        print(f"Ledger: {config['paths']['ledger_file']}")
        print(f"Firma: {config['paths']['ledger_signature_file']}")
        print(f"Audit log: {config['paths']['audit_log_file']}")

    else:
        print(f"Comando sconosciuto: {command}")


if __name__ == "__main__":
    main()
