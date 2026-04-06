from pathlib import Path
import json
import importlib


def load_config(config_path: str = "config.json") -> dict:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file non trovato: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_module_config(module_name: str) -> dict:
    try:
        module_config = importlib.import_module(f"src.modules.{module_name}.config")
    except ModuleNotFoundError:
        raise ValueError(f"Modulo non valido: {module_name}")

    return module_config.load_config()
