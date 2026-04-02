import argparse
import importlib
from pathlib import Path

from cli.run_validation import run_validation
from core.verify_ledger import verify_ledger
from core.verify_ledger_signature import main as verify_signature
from core.config_loader import load_config


GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(text: str):
    print(f"{GREEN}✔ {text}{RESET}")


def fail(text: str):
    print(f"{RED}✘ {text}{RESET}")


def section(title: str):
    print()
    print(f"{BOLD}=== {title} ==={RESET}")


def load_module_config(module_name):
    try:
        module = importlib.import_module(f"modules.{module_name}.config")
        return getattr(module, f"get_{module_name}_config")()
    except Exception as e:
        print(f"❌ Errore caricamento modulo '{module_name}': {e}")
        return None


def show_status(config: dict, module_config: dict):
    section("STATUS")
    print(f"Module: {module_config['module_name']}")
    print(f"Dossier type: {module_config['dossier_type']}")
    print(f"Ledger file: {config['paths']['ledger_file']}")
    print(f"Ledger signature: {config['paths']['ledger_signature_file']}")
    print(f"Audit log: {config['paths']['audit_log_file']}")
    print(f"Validation output dir: {config['paths']['validation_output_dir']}")
    print(f"Fiscal output dir: {config['paths']['fiscal_output_dir']}")

    print()
    print("Esistenza file:")

    if Path(config["paths"]["ledger_file"]).exists():
        ok("ledger presente")
    else:
        fail("ledger assente")

    if Path(config["paths"]["ledger_signature_file"]).exists():
        ok("firma ledger presente")
    else:
        fail("firma ledger assente")

    if Path(config["paths"]["audit_log_file"]).exists():
        ok("audit log presente")
    else:
        fail("audit log assente")


def run_verify(config: dict):
    section("VERIFY")
    ledger_ok = verify_ledger(config["paths"]["ledger_file"])
    signature_ok = verify_signature()

    print()

    if ledger_ok:
        ok("Ledger OK")
    else:
        fail("Ledger FAIL")

    if signature_ok:
        ok("Signature OK")
    else:
        fail("Signature FAIL")

    if ledger_ok and signature_ok:
        ok("System VERIFIED")
    else:
        fail("System FAILED")


def show_audit(config: dict):
    section("AUDIT")

    audit_path = Path(config["paths"]["audit_log_file"])

    if not audit_path.exists():
        fail("Audit log non trovato")
        return

    lines = audit_path.read_text(encoding="utf-8").splitlines()

    if not lines:
        print("Audit log vuoto")
        return

    ok("Ultima entry audit")
    print(lines[-1])


def show_help():
    section("AIDENTITECH ENGINE CLI")
    print("Uso:")
    print("  pharma validate --module pharma")
    print("  pharma validate --module energy")
    print("  pharma validate --module food")
    print("  pharma status --module pharma")
    print("  pharma verify")
    print("  pharma audit")
    print("  pharma help")


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("--module", default="pharma")
    args = parser.parse_args()

    config = load_config()
    module_config = load_module_config(args.module)

    if not module_config:
        print("❌ Config modulo non trovata")
        return

    command = args.command.lower()

    if command == "validate":
        run_validation(config, module_config, verify_ledger, verify_signature)
    elif command == "verify":
        run_verify(config)
    elif command == "status":
        show_status(config, module_config)
    elif command == "audit":
        show_audit(config)
    elif command == "help":
        show_help()
    else:
        fail(f"Comando sconosciuto: {command}")
        show_help()


if __name__ == "__main__":
    main()
