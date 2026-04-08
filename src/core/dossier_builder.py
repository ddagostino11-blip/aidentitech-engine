from datetime import datetime, timezone
import json
import hashlib
import subprocess
import base64
from pathlib import Path
from src.core.crypto_utils import sign_data


# =========================
# CANONICAL JSON + HASH
# =========================
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


# =========================
# FIRMA RSA
# =========================
def sign_hash_with_openssl(hash_hex, private_key_path):
    tmp_file = "tmp_hash.txt"
    sig_file = "tmp_sig.bin"

    with open(tmp_file, "w") as f:
        f.write(hash_hex)

    subprocess.run([
        "openssl", "dgst", "-sha256",
        "-sign", private_key_path,
        "-out", sig_file,
        tmp_file
    ], check=True)

    with open(sig_file, "rb") as f:
        signature = base64.b64encode(f.read()).decode()

    Path(tmp_file).unlink(missing_ok=True)
    Path(sig_file).unlink(missing_ok=True)

    return signature


def sign_json_with_openssl(data, private_key_path):
    payload = canonical_json(data).encode("utf-8")
    return sign_data(payload, private_key_path)


# =========================
# BUILD DOSSIER
# =========================
def build_dossier(risk_result, summary_file, previous_hash=None):
    core_dossier = {
        "dossier_type": "MASTER_PHARMA",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_version": "4.0",
        "policy_version": "1.0",
        "summary_file": summary_file,
        "summary": {},
        "previous_hash": previous_hash,
    }

    bundle_domain = "PHARMA"
    bundle_jurisdiction = "IT"
    bundle_version = "2026.04.08.1"
    bundle_id = f"{bundle_domain}-{bundle_jurisdiction}-2026-04-08-v1"
    bundle_hash = "dev-bundle-hash"

    core_dossier["regulatory_context"] = {
        "bundle_id": bundle_id,
        "bundle_hash": bundle_hash,
        "jurisdiction": bundle_jurisdiction,
        "domain": bundle_domain,
        "version": bundle_version
    }
    core_dossier["execution_path"] = {
        "pipeline_id": "06-14-22-30-46-61"
    }

    core_dossier["risk_decision"] = {
        "risk_score": risk_result["risk_score"],
        "status": risk_result["status"],
        "hard_block": risk_result["hard_block"],
        "reasons": risk_result["reasons"],
        "recommended_action": risk_result["recommended_action"]
    }

    dossier_hash = canonical_hash(core_dossier)
    signature = sign_json_with_openssl(core_dossier, "private_key.pem")

    dossier = dict(core_dossier)
    dossier["dossier_hash"] = dossier_hash
    dossier["signature"] = signature

    return dossier


# =========================
# VERIFY LEDGER CHAIN
# =========================
def verify_ledger_chain(ledger_file):
    if not Path(ledger_file).exists():
        return True

    with open(ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    prev_hash = None

    for i, line in enumerate(lines):
        entry = json.loads(line)

        entry_copy = dict(entry)
        entry_hash = entry_copy.pop("entry_hash", None)

        entry_string = json.dumps(entry_copy, sort_keys=True, ensure_ascii=False)
        computed_hash = hashlib.sha256(entry_string.encode("utf-8")).hexdigest()

        if entry_hash != computed_hash:
            raise ValueError(f"Ledger corrotto alla riga {i}")

        if entry_copy.get("previous_hash") != prev_hash:
            raise ValueError(f"Chain rotta alla riga {i}")

        prev_hash = entry_hash

    return True
