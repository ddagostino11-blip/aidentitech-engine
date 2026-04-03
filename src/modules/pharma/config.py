def get_pharma_config():
    return {
        "module_name": "pharma",
        "dossier_type": "MASTER_PHARMA",
        "engine_version": "1.0",
        "policy_version": "2.0",
        "rules_version": "3.0",
        "rules_hash": "pharma-rules-v3",
        "pipeline_id": "pharma-pipeline-003",

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

            "checks": [
                {
                    "rule_id": "gmp_not_compliant",
                    "type": "boolean_equals",
                    "field": "gmp_compliant",
                    "expected": False,
                    "status": "REJECTED",
                    "severity": "HIGH",
                    "risk_score": 60,
                    "issue_code": "gmp_non_compliant",
                    "recommended_action": "HOLD_BATCH"
                },
                {
                    "rule_id": "temperature_warning_low",
                    "type": "numeric_lt",
                    "field": "temperature",
                    "threshold": 2,
                    "status": "WARNING",
                    "severity": "MEDIUM",
                    "risk_score": 20,
                    "issue_code": "temperature_warning_low",
                    "recommended_action": "QUALITY_REVIEW"
                },
                {
                    "rule_id": "temperature_warning_high",
                    "type": "numeric_gt",
                    "field": "temperature",
                    "threshold": 8,
                    "status": "WARNING",
                    "severity": "MEDIUM",
                    "risk_score": 20,
                    "issue_code": "temperature_warning_high",
                    "recommended_action": "QUALITY_REVIEW"
                },
                {
                    "rule_id": "temperature_critical_low",
                    "type": "numeric_lt",
                    "field": "temperature",
                    "threshold": 0,
                    "status": "CRITICAL",
                    "severity": "CRITICAL",
                    "risk_score": 80,
                    "issue_code": "temperature_critical_low",
                    "recommended_action": "BLOCK_AND_ESCALATE"
                },
                {
                    "rule_id": "temperature_critical_high",
                    "type": "numeric_gt",
                    "field": "temperature",
                    "threshold": 25,
                    "status": "CRITICAL",
                    "severity": "CRITICAL",
                    "risk_score": 80,
                    "issue_code": "temperature_critical_high",
                    "recommended_action": "BLOCK_AND_ESCALATE"
                }
            ],

            "actions": {
                "APPROVED": "RELEASE_BATCH",
                "WARNING": "QUALITY_REVIEW",
                "REJECTED": "HOLD_BATCH",
                "CRITICAL": "BLOCK_AND_ESCALATE"
            }
        }
    }
