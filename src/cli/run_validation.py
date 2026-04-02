from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import subprocess

from src.core.verify_ledger import verify_ledger
from src.core.verify_ledger_signature import main as verify_ledger_signature_main
from src.core.config_loader import load_config

config = load_config()

ledger_file = config["paths"]["ledger_file"]
audit_log_file = config["paths"]["audit_log_file"]


def sign_file_with_openssl(file_path: str, private_key_path: str, output_sig_path: str):
    subprocess.run([
        "openssl", "dgst", "-sha256",
        "-sign", private_key_path,
        "-out", output_sig_path,
        file_path
    ], check=True)


def append_audit_log(entry: dict, audit_path: str = audit_log_file):
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


print("\n=== PREFLIGHT SECURITY CHECK ===")

preflight_ledger_ok = True
preflight_signature_ok = True
first_execution = not Path(ledger_file).exists()

if first_execution:
    print("Ledger assente: prima esecuzione")
else:
    print("Verifica integrità ledger in corso...")
    preflight_ledger_ok = verify_ledger(ledger_file)
    if not preflight_ledger_ok:
        print("❌ BLOCCO SICUREZZA: ledger corrotto")
        raise SystemExit(1)

    if not Path(config["paths"]["ledger_signature_file"]).exists():
        print("❌ BLOCCO SICUREZZA: firma ledger mancante")
        raise SystemExit(1)

    print("Verifica firma ledger...")
    preflight_signature_ok = verify_ledger_signature_main()
    if not preflight_signature_ok:
        print("❌ BLOCCO SICUREZZA: firma ledger NON valida")
        raise SystemExit(1)


risk_result = {
    "risk_score": config["risk_defaults"]["risk_score"],
    "status": config["risk_defaults"]["status"],
    "hard_block": config["risk_defaults"]["hard_block"],
    "reasons": config["risk_defaults"]["reasons"],
    "recommended_action": config["risk_defaults"]["recommended_action"]
}

print("\n=== RISK ENGINE ===")
print(f"Risk score: {risk_result['risk_score']}")
print(f"Status: {risk_result['status']}")
print(f"Hard block: {risk_result['hard_block']}")
print(f"Reasons: {risk_result['reasons']}")
print(f"Recommended action: {risk_result['recommended_action']}")


Path(config["paths"]["validation_output_dir"]).mkdir(parents=True, exist_ok=True)
Path(config["paths"]["fiscal_output_dir"]).mkdir(parents=True, exist_ok=True)
Path("runtime/logs").mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dossier_file = f"{config['paths']['validation_output_dir']}/dossier_{timestamp}.json"
summary_file = f"{config['paths']['validation_output_dir']}/summary_{timestamp}.json"
fiscal_file = f"{config['paths']['fiscal_output_dir']}/fiscale_{timestamp}.json"


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
    "engine_version": config["engine"]["engine_version"],
    "policy_version": config["engine"]["policy_version"],
    "summary_file": summary_file,
    "summary": {},
    "previous_hash": previous_hash,
    "regulatory_context": {
        "rules_version": config["engine"]["rules_version"],
        "rules_hash": config["engine"]["rules_hash"]
    },
    "execution_path": {
        "pipeline_id": config["engine"]["pipeline_id"]
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


sign_file_with_openssl(
    ledger_file,
    config["keys"]["private_key_file"],
    config["paths"]["ledger_signature_file"]
)
print(f"Ledger firmato in: {config['paths']['ledger_signature_file']}")


post_ledger_ok = verify_ledger(ledger_file)
post_signature_ok = verify_ledger_signature_main()

audit_entry = {
    "event_type": "validation_run",
    "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "first_execution": first_execution,
    "dossier_file": dossier_file,
    "summary_file": summary_file,
    "fiscal_file": fiscal_file,
    "dossier_hash": dossier_hash,
    "ledger_file": ledger_file,
    "ledger_signature_file": config["paths"]["ledger_signature_file"],
    "preflight_ledger_ok": preflight_ledger_ok,
    "preflight_signature_ok": preflight_signature_ok,
    "post_ledger_ok": post_ledger_ok,
    "post_signature_ok": post_signature_ok,
    "risk_score": risk_result["risk_score"],
    "risk_status": risk_result["status"],
    "risk_hard_block": risk_result["hard_block"],
    "risk_reasons": risk_result["reasons"],
    "recommended_action": risk_result["recommended_action"]
}

append_audit_log(audit_entry)
print(f"Audit log aggiornato in: {audit_log_file}")

print("\n=== COMPLETATO ===")


def main():
    pass


if __name__ == "__main__":
    main()
