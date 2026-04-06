from src.core.rule_engine import evaluate_rules

def run(module_config, payload):
    rules = module_config.get("rules", [])
    return evaluate_rules(payload or {}, rules)
