import json
import hashlib
from pathlib import Path


def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def canonical_hash(data):
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()

def extract_core_data(dossier: dict) -> dict:
    """
    Deve essere IDENTICO a quello usato in run_validation.py
    """
    return {
        "dossier_type": dossier.get("dossier_type"),
        "generated_at_utc": dossier.get("generated_at_utc"),
        "engine_version": dossier.get("engine_version"),
        "policy_version": dossier.get("policy_version"),
        "summary_file": dossier.get("summary_file"),
        "summary": dossier.get("summary"),
        "previous_hash": dossier.get("previous_hash"),
        "regulatory_context": dossier.get("regulatory_context"),
        "execution_path": dossier.get("execution_path"),
    }

def load_dossiers():
    files = sorted(Path("validation_output").glob("dossier_*.json"))
    dossiers = []

    for f in files:
        with open(f) as fp:
            data = json.load(fp)
            dossiers.append((f.name, data))

    return dossiers


def verify_chain():
    dossiers = load_dossiers()

    print("\n=== CHAIN VERIFICATION (STRICT) ===\n")

    previous_hash = None

    for name, dossier in dossiers:
        print(f"\nChecking: {name}")

        stored_hash = dossier.get("dossier_hash")
        stored_prev = dossier.get("previous_hash")

        if not stored_hash:
            print("❌ INVALID DOSSIER: missing hash")
            return

        core_data = extract_core_data(dossier)
        recalculated_hash = canonical_hash(core_data)

        if stored_hash != recalculated_hash:
            print("❌ HASH TAMPERED")
            print(f"Stored: {stored_hash}")
            print(f"Recalc: {recalculated_hash}")
            return

        if previous_hash and stored_prev != previous_hash:
            print("❌ CHAIN BROKEN")
            return

        print("✔ OK")
        previous_hash = stored_hash

    print("\n✔ FULL CHAIN VALID\n")


if __name__ == "__main__":
    verify_chain()
