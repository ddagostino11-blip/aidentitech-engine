from datetime import datetime, timezone
import json
import hashlib
import subprocess
import base64
from pathlib import Path


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
# FIRMA RSA CON OPENSSL
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

    core_dossier["regulatory_context"] = {
        "rules_version": "1.0",
        "rules_hash": "abc123"
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
    signature = sign_hash_with_openssl(dossier_hash, "private_key.pem")

    dossier = dict(core_dossier)
    dossier["dossier_hash"] = dossier_hash
    dossier["signature"] = signature

    return dossier
