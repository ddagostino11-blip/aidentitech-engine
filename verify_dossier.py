from pathlib import Path
import json
import hashlib
import sys
import subprocess

from src.core.dossier_builder import canonical_hash
from src.core.ledger_utils import verify_ledger_chain_full


def verify_dossier_file(dossier_path_str):
    dossier_path = Path(dossier_path_str)

    if not dossier_path.exists():
        print(f"❌ Dossier non trovato: {dossier_path}")
        return 1

    ledger_path = Path("ledger.jsonl")
    signature_path = Path("ledger.sig")

    print("=== VERIFY DOSSIER ===")

    if not ledger_path.exists():
        print("❌ Ledger assente")
        return 1

    if not signature_path.exists():
        print("❌ Firma ledger assente")
        return 1

    print("1) Verifica chain ledger...")
    try:
        verify_ledger_chain_full(ledger_path)
        print("✅ Chain ledger valida")
    except Exception as e:
        print(f"❌ Chain ledger non valida: {e}")
        return 1

    print("2) Verifica firma ledger...")
    signature_check = subprocess.run(
        ["python3", "src/core/verify_ledger_signature.py"],
        capture_output=True,
        text=True
    )

    if signature_check.stdout:
        print(signature_check.stdout.strip())

    if signature_check.returncode != 0:
        print("❌ Firma ledger non valida")
        if signature_check.stderr:
            print(signature_check.stderr.strip())
        return 1

    print("✅ Firma ledger valida")

    print("3) Carico dossier...")
    with open(dossier_path, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    dossier_hash_in_file = dossier.get("dossier_hash")
    if not dossier_hash_in_file:
        print("❌ dossier_hash mancante nel dossier")
        return 1

    dossier_copy = dict(dossier)
    dossier_copy.pop("dossier_hash", None)
    dossier_copy.pop("signature", None)

    computed_dossier_hash = canonical_hash(dossier_copy)

    if computed_dossier_hash != dossier_hash_in_file:
        print("❌ Hash dossier non valido")
        print(f"Atteso:   {dossier_hash_in_file}")
        print(f"Calcolato:{computed_dossier_hash}")
        return 1

    print("✅ Hash dossier valido")

    print("4) Cerco dossier nel ledger...")
    found = False
    matched_entry = None

    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("dossier_hash") == dossier_hash_in_file:
                found = True
                matched_entry = entry
                break

    if not found:
        print("❌ Dossier non presente nel ledger")
        return 1

    print("✅ Dossier presente nel ledger")

    print("5) Verifica coerenza file...")
    ledger_dossier_file = matched_entry.get("dossier_file")
    if ledger_dossier_file and Path(ledger_dossier_file).name != dossier_path.name:
        print("⚠️ Hash presente nel ledger, ma nome file diverso")
        print(f"Ledger: {ledger_dossier_file}")
        print(f"Input:  {dossier_path}")
    else:
        print("✅ Coerenza file ok")

    print("\n=== ESITO FINALE ===")
    print("✅ DOSSIER CERTIFICATO E VERIFICATO")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 verify_dossier.py <percorso_dossier.json>")
        sys.exit(1)

    sys.exit(verify_dossier_file(sys.argv[1]))
