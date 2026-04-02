import sys
from pathlib import Path

from cli.run_validation import main as validate_main
from core.verify_ledger import verify_ledger
from core.verify_ledger_signature import main as verify_signature
from core.config_loader import load_config


# ===== COLORS =====
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ===== HELPERS =====
def ok(text: str):
    print(f"{GREEN}✔ {text}{RESET}")


def fail(text: str):
    print(f"{RED}✘ {text}{RESET}")


def info(text: str):
    print(f"{BLUE}{text}{RESET}")


def section(title: str):
    print()
    print(f"{BOLD}=== {title} ==={RESET}")


# ===== COMMANDS =====
def show_status(config: dict):
    section("STATUS")

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


def run_verify(config: dict, verbose: bool = False):
    section("VERIFY")

    if verbose:
        # modalità completa (pipeline originale)
        ledger_ok = verify_ledger(config["paths"]["ledger_file"])
        signature_ok = verify_signature()
    else:
        # modalità compatta
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
        info("Audit log vuoto")
        return

    ok("Ultima entry audit")
    print(lines[-1])


def show_help():
    section("PHARMA CLI")

    print("Uso:")
    print("  pharma validate")
    print("  pharma verify [--verbose]")
    print("  pharma status")
    print("  pharma audit")
    print("  pharma help")


# ===== MAIN =====
def main():
    config = load_config()

    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()
    verbose = "--verbose" in sys.argv

    if command == "validate":
        validate_main()

    elif command == "verify":
        run_verify(config, verbose=verbose)

    elif command == "status":
        show_status(config)

    elif command == "audit":
        show_audit(config)

    elif command == "help":
        show_help()

    else:
        fail(f"Comando sconosciuto: {command}")
        show_help()


if __name__ == "__main__":
    main()
