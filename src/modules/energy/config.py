def get_energy_config():
    return {
        "module_name": "energy",
        "dossier_type": "MASTER_ENERGY",
        "engine_version": "1.0",
        "policy_version": "1.0",
        "rules_version": "1.0",
        "rules_hash": "energy-placeholder",
        "pipeline_id": "energy-pipeline-001",

        "risk_defaults": {
            "risk_score": 0,
            "status": "CERTIFIED",
            "hard_block": False,
            "reasons": [],
            "recommended_action": "EMIT_DOSSIER"
        }
    }
