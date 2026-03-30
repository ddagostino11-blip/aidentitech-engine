import json
import hashlib
from pathlib import Path

LEDGER_FILE = "ledger.jsonl"

def compute_entry_hash(entry: dict) -> str:
    data = dict(entry)
    data.pop("entry_hash", None)
    entry_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(entry_string.encode("utf-8")).hexdigest()

def verify_ledger(path: str = LEDGER_FILE):
    ledger_path = Path(path)

    if not ledger_path.exists():
        print("Ledger non trovato")
        return

    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("Ledger vuoto")
        return

    prev_hash = None

    print("\n=== LEDGER VERIFICATION ===\n")

    for idx, line in enumerate(lines, start=1):
        entry = json.loads(line)

        stored_entry_hash = entry.get("entry_hash")
        stored_prev_hash = entry.get("prev_entry_hash")
        recalculated_hash = compute_entry_hash(entry)

        print(f"Entry {idx}")

        if stored_entry_hash != recalculated_hash:
            print("❌ ENTRY HASH NON VALIDO")
            return

        if stored_prev_hash != prev_hash:
            print("❌ LEDGER CHAIN BROKEN")
            return

        print("✔ OK")
        prev_hash = stored_entry_hash

    print("\n✔ LEDGER VALIDO E INTEGRO")

if __name__ == "__main__":
    verify_ledger()
