import json
import hashlib
import base64
import subprocess
import tempfile
from pathlib import Path


def run_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def verify_dossier():
    print("\n=== DOSSIER VERIFICATION ===\n")
    code, out, err = run_command(["python3", "verify_dossier.py"])
    if code == 0 and ("SIGNATURE VALIDA" in out or "DOSSIER VALIDO" in out):
        print(out)
        print("\n✔ DOSSIER CHECK OK")
        return True
    print(out)
    if err:
        print(err)
    print("\n❌ DOSSIER CHECK FAILED")
    return False


def verify_chain():
    print("\n=== CHAIN VERIFICATION ===\n")
    code, out, err = run_command(["python3", "verify_chain.py"])
    if code == 0 and "FULL CHAIN VALID" in out:
        print(out)
        print("\n✔ CHAIN CHECK OK")
        return True
    print(out)
    if err:
        print(err)
    print("\n❌ CHAIN CHECK FAILED")
    return False


def verify_ledger():
    print("\n=== LEDGER VERIFICATION ===\n")
    code, out, err = run_command(["python3", "verify_ledger.py"])
    if code == 0 and "LEDGER VALIDO E INTEGRO" in out:
        print(out)
        print("\n✔ LEDGER CHECK OK")
        return True
    print(out)
    if err:
        print(err)
    print("\n❌ LEDGER CHECK FAILED")
    return False


def verify_ledger_signature():
    print("\n=== LEDGER SIGNATURE VERIFICATION ===\n")
    code, out, err = run_command(["python3", "verify_ledger_signature.py"])
    if code == 0 and "FIRMA LEDGER VALIDA" in out:
        print(out)
        print("\n✔ LEDGER SIGNATURE CHECK OK")
        return True
    print(out)
    if err:
        print(err)
    print("\n❌ LEDGER SIGNATURE CHECK FAILED")
    return False


def inspect_timestamp():
    print("\n=== TIMESTAMP INSPECTION ===\n")

    tsr_path = Path("timestamps/ledger_timestamp.tsr")
    ledger_path = Path("ledger.jsonl")

    if not tsr_path.exists():
        print("❌ Timestamp file non trovato")
        return False

    if not ledger_path.exists():
        print("❌ ledger.jsonl non trovato")
        return False

    code, out, err = run_command([
        "openssl", "ts", "-reply",
        "-in", str(tsr_path),
        "-text"
    ])

    if code != 0:
        print(out)
        if err:
            print(err)
        print("\n❌ TIMESTAMP INSPECTION FAILED")
        return False

    print(out)

    if "Status: Granted." in out or "Status: Granted" in out:
        print("\n✔ TIMESTAMP STATUS OK")
        return True

    print("\n❌ TIMESTAMP STATUS FAILED")
    return False


def main():
    print("\n==============================")
    print(" FULL SYSTEM AUDIT VERIFICATION ")
    print("==============================")

    checks = {
        "dossier": verify_dossier(),
        "chain": verify_chain(),
        "ledger": verify_ledger(),
        "ledger_signature": verify_ledger_signature(),
        "timestamp": inspect_timestamp(),
    }

    print("\n========== FINAL SUMMARY ==========\n")
    for name, ok in checks.items():
        status = "OK" if ok else "FAIL"
        print(f"{name}: {status}")

    if all(checks.values()):
        print("\n✔ FULL SYSTEM VALID")
    else:
        print("\n❌ SOME CHECKS FAILED")


if __name__ == "__main__":
    main()
