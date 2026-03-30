import json
import hashlib
import base64
import subprocess
import tempfile


def canonical_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


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
    }


def canonical_hash(data):
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def verify_signature_with_openssl(digest_hex: str, signature_b64: str, public_key_path: str = "public_key.pem") -> bool:
    signature_bytes = base64.b64decode(signature_b64)

    with tempfile.NamedTemporaryFile(delete=False) as sig_file:
        sig_file.write(signature_bytes)
        sig_path = sig_file.name

    result = subprocess.run(
        ["openssl", "dgst", "-sha256", "-verify", public_key_path, "-signature", sig_path],
        input=digest_hex,
        capture_output=True,
        text=True,
    )
    return "Verified OK" in result.stdout


def main():
    with open("dossier.json", "r", encoding="utf-8") as f:
        dossier = json.load(f)

    stored_hash = dossier.get("dossier_hash")
    signature_b64 = dossier.get("signature")

    if not stored_hash or not signature_b64:
        print("❌ DOSSIER INCOMPLETO")
        return

    core = extract_core_dossier(dossier)
    recalculated_hash = canonical_hash(core)

    print("Stored hash:      ", stored_hash)
    print("Recalculated hash:", recalculated_hash)

    if stored_hash != recalculated_hash:
        print("❌ HASH NON CORRISPONDE")
        return

    valid = verify_signature_with_openssl(recalculated_hash, signature_b64, "public_key.pem")

    if valid:
        print("✔ DOSSIER VALIDO")
    else:
        print("❌ FIRMA NON VALIDA")


if __name__ == "__main__":
    main()
