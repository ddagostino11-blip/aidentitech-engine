import json
import hashlib
import subprocess
import base64
from pathlib import Path


# =========================
# HASH CANONICO
# =========================
def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )


def canonical_hash(data):
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


# =========================
# VERIFICA FIRMA DOSSIER
# =========================
def verify_dossier_signature(dossier):
    print("Verifica firma dossier...")

    if "signature" not in dossier:
        print("❌ Firma mancante nel dossier")
        return False

    signature_b64 = dossier["signature"]

    payload = dict(dossier)
    payload.pop("signature", None)
    payload.pop("dossier_hash", None)

    tmp_payload_file = "tmp_verify_payload.json"
    tmp_sig_file = "tmp_verify_sig.bin"

    with open(tmp_payload_file, "w", encoding="utf-8") as f:
        f.write(canonical_json(payload))

    with open(tmp_sig_file, "wb") as f:
        f.write(base64.b64decode(signature_b64))

    result = subprocess.run(
        [
            "openssl", "dgst", "-sha256",
            "-verify", "public_key.pem",
            "-signature", tmp_sig_file,
            tmp_payload_file
        ],
        capture_output=True,
        text=True
    )

    Path(tmp_payload_file).unlink(missing_ok=True)
    Path(tmp_sig_file).unlink(missing_ok=True)

    print(result.stdout)

    return result.returncode == 0

# =========================
# VERIFY DOSSIER
# =========================
def verify_dossier(dossier_path):
    print("\n=== VERIFY DOSSIER ===")

    # 1) Carico dossier
    print("1) Carico dossier...")
    with open(dossier_path, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    # 2) Verifica chain ledger
    print("2) Verifica chain ledger...")
    chain_check = subprocess.run(
        ["python3", "src/core/verify_ledger.py"],
        capture_output=True,
        text=True
    )
    print(chain_check.stdout)

    if chain_check.returncode != 0:
        print("❌ Chain ledger non valida")
        raise SystemExit(1)

    print("✅ Ledger integro")

    # 3) Verifica firma ledger
    print("3) Verifica firma ledger...")
    sig_check = subprocess.run(
        ["python3", "src/core/verify_ledger_signature.py"],
        capture_output=True,
        text=True
    )
    print(sig_check.stdout)

    if sig_check.returncode != 0:
        print("❌ Firma ledger non valida")
        raise SystemExit(1)

    # 4) Verifica hash dossier
    print("4) Verifica hash dossier...")
    dossier_copy = dict(dossier)
    expected_hash = dossier_copy.pop("dossier_hash")

    if "signature" in dossier_copy:
        dossier_copy.pop("signature")

    computed_hash = canonical_hash(dossier_copy)

    if computed_hash != expected_hash:
        print("❌ Hash dossier NON valido")
        raise SystemExit(1)

    print("✅ Hash dossier valido")

    # 5) Verifica presenza nel ledger
    print("5) Cerco dossier nel ledger...")
    found = False

    with open("ledger.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("dossier_hash") == expected_hash:
                found = True
                break

    if not found:
        print("❌ Dossier NON presente nel ledger")
        raise SystemExit(1)

    print("✅ Dossier presente nel ledger")

    # 6) Verifica firma dossier
    print("6) Verifica firma dossier...")
    if not verify_dossier_signature(dossier):
        print("❌ Firma dossier NON valida")
        raise SystemExit(1)

    print("✅ Firma dossier valida")

    print("\n=== ESITO FINALE ===")
    print("✅ DOSSIER CERTIFICATO E VERIFICATO")


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Uso: python3 verify_dossier.py <dossier_path>")
        raise SystemExit(1)

    verify_dossier(sys.argv[1])
