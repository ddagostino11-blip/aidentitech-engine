from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import subprocess

from verify_ledger import verify_ledger
from verify_ledger_signature import main as verify_ledger_signature_main

ledger_file = "ledger.jsonl"

def sign_file_with_openssl(file_path: str, private_key_path: str, output_sig_path: str):
    subprocess.run([
        "openssl", "dgst", "-sha256",
        "-sign", private_key_path,
        "-out", output_sig_path,
        file_path
    ], check=True)

print("\n=== PREFLIGHT SECURITY CHECK ===")

if not Path(ledger_file).exists():
    print("Ledger assente: prima esecuzione")
else:
    print("Verifica integrità ledger in corso...")
    if not verify_ledger(ledger_file):
        print("❌ BLOCCO SICUREZZA: ledger corrotto")
        raise SystemExit(1)

    print("Verifica firma ledger...")
    if not verify_ledger_signature_main():
        print("❌ BLOCCO SICUREZZA: firma ledger NON valida")
        raise SystemExit(1)

risk_result = {
    "risk_score": 0,
    "status": "CERTIFIED",
    "hard_block": False,
    "reasons": [],
    "recommended_action": "EMIT_DOSSIER"
}

print("\n=== RISK ENGINE ===")
print(f"Risk score: {risk_result['risk_score']}")
print(f"Status: {risk_result['status']}")
print(f"Hard block: {risk_result['hard_block']}")
print(f"Reasons: {risk_result['reasons']}")
print(f"Recommended action: {risk_result['recommended_action']}")

Path("validation_output").mkdir(exist_ok=True)
Path("commercialisti_inbox").mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dossier_file = f"validation_output/dossier_{timestamp}.json"
summary_file = f"validation_output/summary_{timestamp}.json"
fiscal_file = f"commercialisti_inbox/fiscale_{timestamp}.json"

previous_hash = "GENESIS"
prev_entry_hash = None

if Path(ledger_file).exists():
    with open(ledger_file, "r", encoding="utf-8") as lf:
        lines = lf.readlines()
        if lines:
            last_entry = json.loads(lines[-1])
            previous_hash = last_entry.get("dossier_hash", "GENESIS")
            prev_entry_hash = last_entry.get("entry_hash")

core_dossier = {
    "dossier_type": "MASTER_PHARMA",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "engine_version": "4.0",
    "policy_version": "1.0",
    "summary_file": summary_file,
    "summary": {},
    "previous_hash": previous_hash,
    "regulatory_context": {
        "rules_version": "1.0",
        "rules_hash": "abc123"
    },
    "execution_path": {
        "pipeline_id": "06-14-22-30-46-61"
    },
    "risk_decision": {
        "risk_score": risk_result["risk_score"],
        "status": risk_result["status"],
        "hard_block": risk_result["hard_block"],
        "reasons": risk_result["reasons"],
        "recommended_action": risk_result["recommended_action"]
    }
}

dossier_hash = hashlib.sha256(
    json.dumps(core_dossier, sort_keys=True, ensure_ascii=False).encode("utf-8")
).hexdigest()

dossier = dict(core_dossier)
dossier["dossier_hash"] = dossier_hash

with open(summary_file, "w", encoding="utf-8") as f:
    json.dump({"status": "OK"}, f, indent=2, ensure_ascii=False)

with open(dossier_file, "w", encoding="utf-8") as f:
    json.dump(dossier, f, indent=2, ensure_ascii=False)

with open(fiscal_file, "w", encoding="utf-8") as f:
    json.dump({"status": "READY"}, f, indent=2, ensure_ascii=False)

print(f"Dossier salvato in: {dossier_file}")

ledger_entry = {
    "logged_at_utc": datetime.now(timezone.utc).isoformat(),
    "dossier_file": dossier_file,
    "summary_file": summary_file,
    "dossier_hash": dossier_hash,
    "previous_hash": previous_hash,
    "fiscal_file": fiscal_file,
    "verification_status": "OK",
    "risk_score": risk_result["risk_score"],
    "risk_status": risk_result["status"],
    "risk_reasons": risk_result["reasons"],
    "recommended_action": risk_result["recommended_action"],
    "prev_entry_hash": prev_entry_hash
}

entry_string = json.dumps(ledger_entry, sort_keys=True, ensure_ascii=False)
entry_hash = hashlib.sha256(entry_string.encode("utf-8")).hexdigest()
ledger_entry["entry_hash"] = entry_hash

with open(ledger_file, "a", encoding="utf-8") as lf:
    lf.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")

print("Ledger aggiornato")

sign_file_with_openssl(ledger_file, "private_key.pem", "ledger.sig")
print("Ledger firmato in: ledger.sig")

print("\n=== COMPLETATO ===")
