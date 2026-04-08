from pathlib import Path
import json
import hashlib


def verify_ledger_chain_full(ledger_file):
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
            raise ValueError(f"Ledger corrotto alla entry {i + 1}: hash non valido")

        if entry_copy.get("previous_hash") != prev_hash:
            raise ValueError(f"Chain non valida alla entry {i + 1}")

        prev_hash = entry_hash

    return True
