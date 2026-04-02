from pathlib import Path
import subprocess
import sys

def main():
    ledger_file = "ledger.jsonl"
    signature_file = "ledger.sig"
    public_key = "public_key.pem"

    if not Path(ledger_file).exists():
        print("❌ Ledger non trovato")
        return False

    if not Path(signature_file).exists():
        print("❌ Firma ledger non trovata")
        return False

    if not Path(public_key).exists():
        print("❌ Chiave pubblica non trovata")
        return False

    result = subprocess.run([
        "openssl", "dgst", "-sha256",
        "-verify", public_key,
        "-signature", signature_file,
        ledger_file
    ], capture_output=True, text=True)

    out = (result.stdout or "").strip()
    if out:
        print(out)

    if result.returncode == 0:
        print("✅ FIRMA LEDGER VALIDA")
        return True

    print("❌ FIRMA LEDGER NON VALIDA")
    err = (result.stderr or "").strip()
    if err:
        print(err)
    return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
