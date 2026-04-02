from pathlib import Path
import subprocess

from src.core.config_loader import load_config


def main():
    config = load_config()

    ledger_file = config["paths"]["ledger_file"]
    signature_file = config["paths"]["ledger_signature_file"]
    public_key = config["keys"]["public_key_file"]

    if not Path(ledger_file).exists():
        print("❌ Ledger non trovato")
        return False

    if not Path(signature_file).exists():
        print("❌ Firma ledger non trovata")
        return False

    if not Path(public_key).exists():
        print("❌ Chiave pubblica non trovata")
        return False

    try:
        subprocess.run([
            "openssl", "dgst", "-sha256",
            "-verify", public_key,
            "-signature", signature_file,
            ledger_file
        ], check=True, capture_output=True)

        print("Verified OK")
        print("✅ FIRMA LEDGER VALIDA")
        return True

    except subprocess.CalledProcessError:
        print("❌ FIRMA LEDGER NON VALIDA")
        return False


if __name__ == "__main__":
    main()
