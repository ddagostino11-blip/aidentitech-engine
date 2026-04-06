def load_config():
    return {
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
                    "rule_type": "boolean_equals",
                    "field": "gmp_compliant",
                    "expected": False,
                    "severity": "HIGH",
                    "recommended_action": "HOLD_BATCH"
                },
                {
                    "rule_id": "temperature_warning_high",
                    "rule_type": "numeric_gt",
                    "field": "temperature",
                    "expected": 8,
                    "severity": "MEDIUM",
                    "recommended_action": "QUALITY_REVIEW"
                }
            ]
        },
        "compliance_scope": {
            "frameworks": ["GMP", "GCP", "ICH Q9"],
            "criticality": "HIGH"
        }
    }
