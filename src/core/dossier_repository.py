import json
from pathlib import Path

DOSSIER_DIR = Path("runtime/dossiers")
DOSSIER_DIR.mkdir(parents=True, exist_ok=True)


def save_dossier(client_id: str, dossier: dict) -> str:
    file_path = DOSSIER_DIR / f"{client_id}.json"

    with open(file_path, "w") as f:
        json.dump(dossier, f, indent=2)

    return str(file_path)


def load_dossier(client_id: str) -> dict | None:
    file_path = DOSSIER_DIR / f"{client_id}.json"

    if not file_path.exists():
        return None

    with open(file_path) as f:
        return json.load(f)
