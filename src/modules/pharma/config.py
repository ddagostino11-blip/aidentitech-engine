def get_pharma_config():
    return {
        "module_name": "pharma",
        "dossier_type": "MASTER_PHARMA",
        "engine_version": "4.0",
        "policy_version": "1.0",
        "rules_version": "1.0",
        "rules_hash": "abc123",
        "pipeline_id": "06-14-22-30-46-61",

        "risk_defaults": {
            "risk_score": 0,
            "status": "CERTIFIED",
            "hard_block": False,
            "reasons": [],
            "recommended_action": "EMIT_DOSSIER"
        }
    }
