from src.modules.pharma.logic import run as run_pharma


def run_module(module: str, module_config: dict, payload: dict):
    if module == "pharma":
        return run_pharma(module_config, payload)

    raise ValueError(f"Unsupported module: {module}")
