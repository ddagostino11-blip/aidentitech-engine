import json
import hashlib
import base64
import subprocess
import tempfile
import glob

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

def extract_core_dossier(dossier):
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
        "risk_decision": dossier.get("risk_decision"),
    }

def verify_signature(dossier_file, public_key="public_key.pem"):
    with open(dossier_file, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    stored_hash = dossier.get("dossier_hash")
    signature_b64 = dossier.get("signature")

    # ===== CONTROLLI STRUTTURA =====
    if "regulatory_context" not in dossier:
        print("❌ MISSING regulatory_context")
        return

    if "rules_version" not in dossier["regulatory_context"]:
        print("❌ MISSING rules_version")
        return

    if "rules_hash" not in dossier["regulatory_context"]:
        print("❌ MISSING rules_hash")
        return

    if "execution_path" not in dossier:
        print("❌ MISSING execution_path")
        return

    if "pipeline_id" not in dossier["execution_path"]:
        print("❌ MISSING pipeline_id")
        return

    if not stored_hash or not signature_b64:
        print("❌ DOSSIER INCOMPLETO")
        return

    core_dossier = extract_core_dossier(dossier)
    recalculated_hash = canonical_hash(core_dossier)

    print("Stored hash:", stored_hash)
    print("Recalculated hash:", recalculated_hash)

    if stored_hash != recalculated_hash:
        print("❌ HASH NON CORRISPONDE (FILE TAMPERED)")
        return

    signature = base64.b64decode(signature_b64)

    with tempfile.NamedTemporaryFile(delete=False) as tmp_data:
        tmp_data.write(stored_hash.encode("utf-8"))
        tmp_data_path = tmp_data.name

    with tempfile.NamedTemporaryFile(delete=False) as tmp_sig:
        tmp_sig.write(signature)
        tmp_sig_path = tmp_sig.name

    result = subprocess.run(
        [
            "openssl", "dgst", "-sha256",
            "-verify", public_key,
            "-signature", tmp_sig_path,
            tmp_data_path
        ],
        capture_output=True,
        text=True
    )

    if "Verified OK" in result.stdout:
        print("✔ SIGNATURE VALIDA")
    else:
        print("❌ SIGNATURE NON VALIDA")


if __name__ == "__main__":
    files = sorted(glob.glob("validation_output/dossier_*.json"), reverse=True)

    if not files:
        print("❌ Nessun dossier trovato")
    else:
        verify_signature(files[0])
