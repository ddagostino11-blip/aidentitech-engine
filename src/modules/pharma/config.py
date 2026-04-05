import json
from pathlib import Path


def get_pharma_config():
    rules_path = Path(__file__).with_name("pharma_rules.json")

    with open(rules_path, "r", encoding="utf-8") as f:
        rules_data = json.load(f)

    return {
        "module_name": "pharma",
        "dossier_type": "MASTER_PHARMA",
        "engine_version": "1.0",
        "policy_version": "2.0",
        "rules_version": "4.0",
        "rules_hash": "pharma-rules-json-v4",
        "pipeline_id": "pharma-pipeline-004",

        "risk_defaults": {
            "risk_score": 0,
            "status": "CERTIFIED",
            "hard_block": False,
            "reasons": [],
            "recommended_action": "EMIT_DOSSIER"
        },

        "rules": rules_data
    }
