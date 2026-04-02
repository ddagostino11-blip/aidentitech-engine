from pathlib import Path
import json
import hashlib
import sys

def verify_ledger(ledger_file="ledger.jsonl"):
    if not Path(ledger_file).exists():
        print("Ledger assente (prima esecuzione)")
        return True

    with open(ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    prev_hash = None

    for i, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except Exception:
            print(f"❌ JSON NON VALIDO (entry {i})")
            return False

        entry_copy = dict(entry)
        stored_hash = entry_copy.pop("entry_hash", None)

        recalculated = hashlib.sha256(
            json.dumps(entry_copy, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        if stored_hash != recalculated:
            print(f"❌ ENTRY HASH NON VALIDO (entry {i})")
            return False

        if prev_hash is not None and entry.get("prev_entry_hash") != prev_hash:
            print(f"❌ CHAIN NON VALIDA (entry {i})")
            return False

        prev_hash = stored_hash

    print("✅ Ledger integro")
    return True

if __name__ == "__main__":
    sys.exit(0 if verify_ledger() else 1)
