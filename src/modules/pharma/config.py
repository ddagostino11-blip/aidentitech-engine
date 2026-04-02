def get_pharma_config():
    return {
        "module_name": "pharma",
        "dossier_type": "MASTER_PHARMA",
        "engine_version": "1.0",
        "policy_version": "2.0",
        "rules_version": "2.0",
        "rules_hash": "pharma-rules-v2",
        "pipeline_id": "pharma-pipeline-002",
        "risk_defaults": {
            "risk_score": 0,
            "status": "CERTIFIED",
            "hard_block": False,
            "reasons": [],
            "recommended_action": "EMIT_DOSSIER"
        },
        "rules": {
            "required_fields": [
                "product_id",
                "batch",
                "gmp_compliant",
                "temperature"
            ],
            "temperature": {
                "min": 2,
                "max": 8,
                "critical_min": 0,
                "critical_max": 25
            },
            "risk_weights": {
                "missing_field": 25,
                "gmp_non_compliant": 60,
                "temperature_warning": 20,
                "temperature_critical": 80
            },
            "actions": {
                "APPROVED": "RELEASE_BATCH",
                "WARNING": "QUALITY_REVIEW",
                "REJECTED": "HOLD_BATCH",
                "CRITICAL": "BLOCK_AND_ESCALATE"
            }
        }
    }
