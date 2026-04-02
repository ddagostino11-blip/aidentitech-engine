import sys
from pathlib import Path

from cli.run_validation import main as validate_main
from core.verify_ledger import verify_ledger
from core.verify_ledger_signature import main as verify_signature
from core.config_loader import load_config


def show_status(config: dict):
    print("=== STATUS ===")
    print(f"Ledger file: {config['paths']['ledger_file']}")
    print(f"Ledger signature: {config['paths']['ledger_signature_file']}")
    print(f"Audit log: {config['paths']['audit_log_file']}")
    print(f"Validation output dir: {config['paths']['validation_output_dir']}")
    print(f"Fiscal output dir: {config['paths']['fiscal_output_dir']}")
    print()
    print("Esistenza file:")
    print(f"ledger: {Path(config['paths']['ledger_file']).exists()}")
    print(f"signature: {Path(config['paths']['ledger_signature_file']).exists()}")
    print(f"audit log: {Path(config['paths']['audit_log_file']).exists()}")


def run_verify(config: dict):
    print("=== VERIFY ===")
    ledger_ok = verify_ledger(config["paths"]["ledger_file"])
    signature_ok = verify_signature()

    if ledger_ok and signature_ok:
        print("✅ Sistema verificato OK")
    else:
        print("❌ Verifica fallita")


def show_audit(config: dict):
    print("=== AUDIT ===")
    audit_path = Path(config["paths"]["audit_log_file"])

    if not audit_path.exists():
        print("❌ Audit log non trovato")
        return

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        print("Audit log vuoto")
        return

    print(lines[-1])


def main():
    config = load_config()

    if len(sys.argv) < 2:
        print("Uso: pharma [validate | verify | status | audit]")
        return

    command = sys.argv[1].lower()

    if command == "validate":
        validate_main()
    elif command == "verify":
        run_verify(config)
    elif command == "status":
        show_status(config)
    elif command == "audit":
        show_audit(config)
    else:
        print(f"Comando sconosciuto: {command}")
        print("Uso: pharma [validate | verify | status | audit]")


if __name__ == "__main__":
    main()
