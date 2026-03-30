from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import subprocess
import tempfile
import base64

def create_timestamp(file_path: str, output_name: str):
    tsq_file = f"timestamps/{output_name}.tsq"
    tsr_file = f"timestamps/{output_name}.tsr"

    Path("timestamps").mkdir(exist_ok=True)

    subprocess.run([
        "openssl", "ts", "-query",
        "-data", file_path,
        "-sha256",
        "-out", tsq_file
    ], check=True)

    subprocess.run([
        "curl", "-s",
        "-H", "Content-Type: application/timestamp-query",
        "--data-binary", f"@{tsq_file}",
        "https://freetsa.org/tsr",
        "-o", tsr_file
    ], check=True)

    print(f"Timestamp creato: {tsr_file}")

# ===== LOAD RULES =====
with open("rules/pharma_v1.json", "r", encoding="utf-8") as rf:
    rules_data = json.load(rf)

rules_version = rules_data.get("version", "unknown")

rules_bytes = json.dumps(rules_data, sort_keys=True).encode("utf-8")
rules_hash = hashlib.sha256(rules_bytes).hexdigest()
from shield_unified_sovereign import DoodogUnifiedSovereign, PolicyBundle
from validation_pack import ShieldValidationRunner


# =========================
# HELPERS
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


def load_last_dossier_hash(output_dir: Path):
    files = sorted(output_dir.glob("dossier_*.json"))
    if not files:
        return None
    with open(files[-1], "r", encoding="utf-8") as f:
        d = json.load(f)
    return d.get("dossier_hash")


def normalize_summary(summary):
    if isinstance(summary, str):
        try:
            parsed = json.loads(summary)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {"raw_summary": summary}

    if hasattr(summary, "__dict__"):
        return json.loads(json.dumps(summary.__dict__, default=str))

    if isinstance(summary, dict):
        return summary

    return json.loads(json.dumps(summary, default=str))


def build_core_dossier(engine_version, policy_version, summary_file, summary_json, previous_hash):
    return {
        "dossier_type": "validation_dossier",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_version": engine_version,
        "policy_version": policy_version,
        "summary_file": str(summary_file),
        "summary": summary_json,
        "previous_hash": previous_hash,
    }


def sign_hash_with_openssl(digest_hex: str, private_key_path: str = "private_key.pem") -> str:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(digest_hex.encode("utf-8"))
        tmp_path = tmp.name

    try:
        signature_bytes = subprocess.check_output(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-sign",
                private_key_path,
                tmp_path,
            ],
            stderr=subprocess.STDOUT,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return base64.b64encode(signature_bytes).decode("utf-8")


# =========================
# MOCK SERVICES FOR KERNEL
# =========================

class MockHSMVault:
    def sign_canonical_digest(self, digest: str) -> str:
        return f"sig::{digest}"

    def verify_signature(self, digest: str, signature: str) -> bool:
        return signature == f"sig::{digest}"


class MockNTPService:
    def get_trusted_time(self) -> str:
        return datetime.now(timezone.utc).isoformat()


# =========================
# KERNEL ADAPTER
# =========================

class KernelAdapter:
    def __init__(self, kernel):
        self.kernel = kernel
        self.policy = getattr(kernel, "policy", None)
        self.engine_version = getattr(kernel, "engine_version", "UNKNOWN")

    def execute_elite_pipeline_ultimate(self, user_session, audit_input):
        result = self.kernel.execute(user_session, audit_input)

        if isinstance(result, dict) and result.get("status") == "CRITICAL_ERROR":
            return {
                "status": "REJECTED",
                "reason": "CRITICAL_ERROR_DOWNGRADED_TO_REJECTED",
                "original_result": result,
                "case_id": result.get("case_id"),
            }

        return result


# =========================
# POLICY
# =========================

policy = PolicyBundle(
    version="2026.Q2.TEST",
    expected_terms_hash="EXPECTED_HASH",
    hsm_key_id="TEST_KEY",
    signature_algorithm="mock-sha256",
    thresholds={
        "be_lower": 80.0,
        "be_upper": 125.0,
        "cooks": 1.0,
        "leverage": 0.5,
    },
)

base_kernel = DoodogUnifiedSovereign(
    hsm_vault=MockHSMVault(),
    ntp_service=MockNTPService(),
    policy_bundle=policy,
    storage_path="./forensic_store",
)

kernel = KernelAdapter(base_kernel)


# =========================
# RUN VALIDATION
# =========================

runner = ShieldValidationRunner(kernel)
summary = runner.run_smoke_suite()
summary_json = normalize_summary(summary)


# =========================
# OUTPUT FILES
# =========================

output_dir = Path("./validation_output")
output_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
summary_file = output_dir / f"summary_{timestamp}.json"
dossier_file = output_dir / f"dossier_{timestamp}.json"

with open(summary_file, "w", encoding="utf-8") as f:
    json.dump(summary_json, f, indent=2, default=str)

if isinstance(summary_json, dict):
    total = summary_json.get("total")
    passed = summary_json.get("passed")
    failed = summary_json.get("failed")
else:
    total = passed = failed = None

previous_hash = load_last_dossier_hash(output_dir)

core_dossier = build_core_dossier(
    engine_version=kernel.engine_version,
    policy_version=policy.version,
    summary_file=summary_file,
    summary_json=summary_json,
    previous_hash=previous_hash,
)

core_dossier["regulatory_context"] = {
    "rules_version": rules_version,
    "rules_hash": rules_hash
}

core_dossier["execution_path"] = {
    "pipeline_id": "06-14-22-30-46-61"
}

dossier_hash = canonical_hash(core_dossier)

# FIRMA REALE RSA CON OPENSSL
signature = sign_hash_with_openssl(dossier_hash, "private_key.pem")

dossier = dict(core_dossier)
dossier["result_overview"] = {
    "total": total,
    "passed": passed,
    "failed": failed,
}
dossier["dossier_hash"] = dossier_hash
dossier["signature"] = signature

with open(dossier_file, "w", encoding="utf-8") as f:
    json.dump(dossier, f, indent=2, default=str)

# ===== IMMUTABLE STORAGE =====
from pathlib import Path
import os

immutable_dir = Path("storage/immutable")
immutable_dir.mkdir(parents=True, exist_ok=True)

immutable_file = immutable_dir / Path(dossier_file).name

with open(dossier_file, "r", encoding="utf-8") as src, open(immutable_file, "w", encoding="utf-8") as dst:
    dst.write(src.read())

os.chmod(immutable_file, 0o444)

print(f"Salvato in immutable: {immutable_file}")


# ===== BACKUP =====
backup_dir = Path("storage/backup")
backup_dir.mkdir(parents=True, exist_ok=True)

backup_file = backup_dir / Path(dossier_file).name

with open(dossier_file, "r", encoding="utf-8") as src, open(backup_file, "w", encoding="utf-8") as dst:
    dst.write(src.read())

print(f"Backup creato: {backup_file}")

# ===== EXPORT FISCALE AUTOMATICO =====
fiscal_data = {
    "dossier_hash": dossier_hash,
    "generated_at_utc": dossier.get("generated_at_utc"),
    "engine_version": dossier.get("engine_version"),
    "policy_version": dossier.get("policy_version"),
    "result_overview": dossier.get("result_overview"),
    "signature": signature
}

commercialisti_dir = Path("commercialisti_inbox")
commercialisti_dir.mkdir(exist_ok=True)

fiscal_filename = f"fiscale_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
fiscal_file = commercialisti_dir / fiscal_filename

with open(fiscal_file, "w", encoding="utf-8") as ff:
    json.dump(fiscal_data, ff, indent=2, default=str)

print(f"Dati fiscali inviati a: {fiscal_file}")

# =========================
# OUTPUT
# =========================

print("\n==============================")
print("VALIDATION COMPLETATA")
print("==============================")
print(f"Summary salvato in: {summary_file}")
print(f"Dossier salvato in: {dossier_file}")
print(f"Previous hash: {previous_hash}")
print(f"Dossier hash: {dossier_hash}")
print(f"Signature (base64): {signature[:80]}...")

# ===== VERIFICA AUTOMATICA POST-SALVATAGGIO =====
verify_result = subprocess.run(
    ["python3", "verify_dossier.py"],
    capture_output=True,
    text=True
)

print("\n=== VERIFICA AUTOMATICA ===")
print(verify_result.stdout)

verification_status = "OK" if "SIGNATURE VALIDA" in verify_result.stdout else "FAIL"

# ===== AUDIT LOG UNICO =====
audit_log = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "dossier_file": str(dossier_file),
    "summary_file": str(summary_file),
    "dossier_hash": dossier_hash,
    "fiscal_file": str(fiscal_file),
    "verification_status": verification_status
}
with open("audit_log.json", "w", encoding="utf-8") as af:
    json.dump(audit_log, af, indent=2, default=str)

print("Audit log salvato in: audit_log.json")

# ===== APPEND-ONLY LEDGER (HASH LINKED) =====

import hashlib

ledger_file = "ledger.jsonl"

# recupera hash ultima entry
prev_entry_hash = None
if Path(ledger_file).exists():
    with open(ledger_file, "r", encoding="utf-8") as lf:
        lines = lf.readlines()
        if lines:
            last_entry = json.loads(lines[-1])
            prev_entry_hash = last_entry.get("entry_hash")

ledger_entry = {
    "logged_at_utc": datetime.now(timezone.utc).isoformat(),
    "dossier_file": str(dossier_file),
    "summary_file": str(summary_file),
    "dossier_hash": dossier_hash,
    "previous_hash": previous_hash,
    "fiscal_file": str(fiscal_file),
    "verification_status": verification_status,
    "prev_entry_hash": prev_entry_hash
}

# calcolo hash entry
entry_string = json.dumps(ledger_entry, sort_keys=True, ensure_ascii=False)
entry_hash = hashlib.sha256(entry_string.encode("utf-8")).hexdigest()

ledger_entry["entry_hash"] = entry_hash

# append
with open(ledger_file, "a", encoding="utf-8") as lf:
    lf.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")

print("Ledger hash-linked aggiornato")

# ===== FIRMA DEL LEDGER =====
with open(ledger_file, "rb") as lf:
    ledger_bytes = lf.read()

ledger_hash = hashlib.sha256(ledger_bytes).hexdigest()
ledger_signature = sign_hash_with_openssl(ledger_hash, "private_key.pem")

with open("ledger.sig", "w", encoding="utf-8") as sf:
    sf.write(ledger_signature)

print("Ledger firmato in: ledger.sig")

# ===== TIMESTAMP LEDGER =====
create_timestamp("ledger.jsonl", "ledger_timestamp")

# ===== CLIENT PROOF PACKAGE =====

client_dir = Path("client_proof")
client_dir.mkdir(exist_ok=True)

# copia dossier
client_dossier = client_dir / "dossier.json"
with open(dossier_file, "r", encoding="utf-8") as src, open(client_dossier, "w", encoding="utf-8") as dst:
    dst.write(src.read())

# copia signature
client_signature = client_dir / "signature.sig"
with open("ledger.sig", "r", encoding="utf-8") as src, open(client_signature, "w", encoding="utf-8") as dst:
    dst.write(src.read())

# copia public key
client_pubkey = client_dir / "public_key.pem"
with open("public_key.pem", "r", encoding="utf-8") as src, open(client_pubkey, "w", encoding="utf-8") as dst:
    dst.write(src.read())

print("Client proof generato in: client_proof/")
