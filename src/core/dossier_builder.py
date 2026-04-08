import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import base64


# ============================
# CANONICAL JSON + HASH
# ============================
def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def canonical_hash(data):
    return hashlib.sha256(
        canonical_json(data).encode("utf-8")
    ).hexdigest()


# ============================
# FIRMA HASH CON OPENSSL
# ============================
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
