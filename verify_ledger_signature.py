import hashlib
import base64
import subprocess
import tempfile


def verify_signature_with_openssl(digest_hex: str, signature_b64: str, public_key_path: str = "public_key.pem") -> bool:
    import base64
    import subprocess
    import tempfile

    signature_bytes = base64.b64decode(signature_b64)

    with tempfile.NamedTemporaryFile(delete=False) as sig_file:
        sig_file.write(signature_bytes)
        sig_path = sig_file.name

    try:
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", public_key_path, "-signature", sig_path],
            input=digest_hex,
            capture_output=True,
            text=True,
        )
        return "Verified OK" in result.stdout
    finally:
        pass

def main():
    print("\n=== LEDGER SIGNATURE VERIFICATION ===\n")

    with open("ledger.jsonl", "rb") as lf:
        ledger_bytes = lf.read()

    recalculated_hash = hashlib.sha256(ledger_bytes).hexdigest()

    with open("ledger.sig", "r", encoding="utf-8") as sf:
        signature_b64 = sf.read().strip()

    print("Ledger hash:", recalculated_hash)

    valid = verify_signature_with_openssl(
        recalculated_hash,
        signature_b64,
        "public_key.pem"
    )

    if valid:
        print("✔ FIRMA LEDGER VALIDA")
    else:
        print("❌ FIRMA LEDGER NON VALIDA")


if __name__ == "__main__":
    main()
