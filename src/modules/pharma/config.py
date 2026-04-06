import json
from pathlib import Path


def get_pharma_config():
    rules_path = Path(__file__).with_name("pharma_rules.json")

    with open(rules_path, "r", encoding="utf-8") as f:
        rules_data = json.load(f)

    return {
        "module_name": "pharma",
        "dossier_type": "MASTER_PHARMA",

        # VERSIONING (ENGINE LEVEL)
        "engine_version": "1.0",
        "policy_version": "2.0",
        "rules_version": "4.0",
        "rules_hash": "pharma-rules-json-v4",
        "pipeline_id": "pharma-pipeline-004",

        # METADATA
        "metadata": {
            "domain": "pharma",
            "jurisdictions": ["EU", "US"],
            "authorities": ["EMA", "FDA"]
        },

        # COMPLIANCE SCOPE (GOLD LEVEL)
        "compliance_scope": {
            "frameworks": [
                "GMP",
                "GCP",
                "ICH Q9",
                "GAMP 5",
                "ALCOA+"
            ],
            "criticality": "HIGH",
            "regulated": True,
            "requires_audit_trail": True
        },

        # VERSION BLOCK (AUDIT READY)
        "versioning": {
            "engine_version": "1.0",
            "policy_version": "2.0",
            "rules_version": "4.0",
            "rules_hash": "pharma-rules-json-v4"
        },

        # DEFAULT RISK OUTPUT
        "risk_defaults": {
            "risk_score": 0,
            "status": "CERTIFIED",
            "hard_block": False,
            "reasons": [],
            "recommended_action": "EMIT_DOSSIER"
        },

        # RULESET
        "rules": rules_data
    }

def load_config():
    return get_pharma_config()
