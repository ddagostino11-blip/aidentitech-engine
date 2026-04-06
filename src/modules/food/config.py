import json
from pathlib import Path

def load_config():
    rules_path = Path(__file__).parent / "food_rules.json"

    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    return {
        "module_name": "food",
        "dossier_type": "food_compliance",
        "engine_version": "4.0",
        "policy_version": "1.0",
        "rules_version": "1.0",
        "rules_hash": "food-rules-v1",
        "pipeline_id": "food-pipeline-001",
        "risk_defaults": {
            "risk_score": 0,
            "status": "CERTIFIED",
            "hard_block": False,
            "reasons": [],
            "recommended_action": "EMIT_DOSSIER"
        },
        "rules": rules["rules"]
    }
