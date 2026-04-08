from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import subprocess
import base64

from core.dossier_builder import (
    canonical_json,
    canonical_hash,
    sign_hash_with_openssl,
    build_dossier,
)

from core.ledger_utils import verify_ledger_chain_full

# =========================
# PREFLIGHT SICUREZZA LEDGER
# =========================
def preflight_security_check():
    print("\n=== PREFLIGHT SECURITY CHECK ===")

    ledger_path = Path("ledger.jsonl")
    signature_path = Path("ledger.sig")

    # Prima esecuzione
    if not ledger_path.exists():
        print("Ledger assente: prima esecuzione")
        return

    # =========================
    # VERIFICA CHAIN COMPLETA
    # =========================
    print("Verifica integrità ledger in corso...")

    if not verify_ledger_chain_full(ledger_path):
        print("❌ BLOCCO SICUREZZA: ledger non integro")
        exit(1)

    print("✅ Ledger integro")

    # =========================
    # VERIFICA FIRMA
    # =========================
    if not signature_path.exists():
        print("❌ BLOCCO SICUREZZA: firma ledger mancante")
        exit(1)

    print("Verifica firma ledger in corso...")

    signature_check = subprocess.run(
        ["python3", "src/core/verify_ledger_signature.py"],
        capture_output=True,
        text=True
    )

    print(signature_check.stdout)

    if signature_check.returncode != 0:
        print("❌ BLOCCO SICUREZZA: firma ledger non valida")
        if signature_check.stderr:
            print(signature_check.stderr)
        exit(1)

    print("✅ Firma ledger valida")

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    # 🔒 SICUREZZA PRIMA DI TUTTO
    preflight_security_check()

    print("\n=== RISK ENGINE ===")

    # -------------------------
    # SIMULAZIONE RISK ENGINE
    # -------------------------
    risk_result = {
        "risk_score": 0,
        "status": "CERTIFIED",
        "hard_block": False,
        "reasons": [],
        "recommended_action": "EMIT_DOSSIER"
    }

    print(f"Risk score: {risk_result['risk_score']}")
    print(f"Status: {risk_result['status']}")
    print(f"Hard block: {risk_result['hard_block']}")
    print(f"Reasons: {risk_result['reasons']}")
    print(f"Recommended action: {risk_result['recommended_action']}")

    # -------------------------
    # BUILD DOSSIER
summary_file = "validation_output/summary.json"
dossier_file = f"validation_output/dossier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
fiscal_file = "commercialisti_inbox/fiscale.json"

Path("validation_output").mkdir(exist_ok=True)

previous_hash = None

dossier = build_dossier(
    risk_result=risk_result,
    summary_file=summary_file,
    previous_hash=previous_hash,
)

with open(dossier_file, "w", encoding="utf-8") as f:
    json.dump(dossier, f, indent=2, ensure_ascii=False)

print(f"Dossier salvato in: {dossier_file}")

# ============================
# LEDGER ENTRY
# ============================
ledger_file = "ledger.jsonl"
verify_ledger_chain_full(ledger_file)

prev_entry_hash = None
if Path(ledger_file).exists():
    with open(ledger_file, "r") as lf:
        lines = lf.readlines()
        if lines:
            last_entry = json.loads(lines[-1])
            prev_entry_hash = last_entry.get("entry_hash")

ledger_entry = {
    "logged_at_utc": datetime.now(timezone.utc).isoformat(),
    "dossier_file": dossier_file,
    "summary_file": summary_file,
    "dossier_hash": dossier["dossier_hash"],
    "previous_hash": prev_entry_hash,
    "fiscal_file": fiscal_file,
    "verification_status": "OK",

    # 🔥 RISK NEL LEDGER
    "risk_score": risk_result["risk_score"],
    "risk_status": risk_result["status"],
    "risk_reasons": risk_result["reasons"],
    "recommended_action": risk_result["recommended_action"],
}

entry_string = json.dumps(ledger_entry, sort_keys=True, ensure_ascii=False)
entry_hash = hashlib.sha256(entry_string.encode("utf-8")).hexdigest()

ledger_entry["entry_hash"] = entry_hash

with open(ledger_file, "a", encoding="utf-8") as lf:
    lf.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")

print("Ledger aggiornato")

# =========================
# FIRMA DEL LEDGER COMPLETO
# =========================
ledger_path = Path(ledger_file)

if ledger_path.exists():
    with open(ledger_path, "rb") as lf:
        ledger_bytes = lf.read()

    tmp_ledger = "tmp_ledger.bin"
    tmp_sig = "ledger.sig"

    with open(tmp_ledger, "wb") as f:
        f.write(ledger_bytes)

    subprocess.run([
        "openssl", "dgst", "-sha256",
        "-sign", "private_key.pem",
        "-out", tmp_sig,
        tmp_ledger
    ], check=True)

    Path(tmp_ledger).unlink(missing_ok=True)

    print("Ledger firmato in: ledger.sig")

print("\n=== COMPLETATO ===")
