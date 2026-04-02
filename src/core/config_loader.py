from pathlib import Path
import json


def load_config(config_path: str = "config.json") -> dict:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file non trovato: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
