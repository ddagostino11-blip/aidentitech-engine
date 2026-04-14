import json
from pathlib import Path


def _load_rules():
    rules_path = Path(__file__).with_name("pharma_rules.json")

    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_pharma_config():
    rules_data = _load_rules()

    return {
        # =========================
        # IDENTITÀ MODULO
        # =========================
        "module_name": "pharma",
        "dossier_type": "MASTER_PHARMA",

        # =========================
        # VERSIONING (UNICO BLOCCO)
        # =========================
        "versioning": {
            "engine_version": "1.0",
            "policy_version": "2.0",
            "rules_version": "4.0",
            "rules_hash": "pharma-rules-json-v4",
            "pipeline_id": "pharma-pipeline-004",
        },

        # =========================
        # METADATA (DOMINIO → OK QUI)
        # =========================
        "metadata": {
            "domain": "pharma",
            "jurisdictions": ["EU", "US"],
            "authorities": ["EMA", "FDA"],
        },

        # =========================
        # COMPLIANCE SCOPE
        # =========================
        "compliance_scope": {
            "frameworks": [
                "GMP",
                "GCP",
                "ICH Q9",
                "GAMP 5",
                "ALCOA+",
            ],
            "criticality": "HIGH",
            "regulated": True,
            "requires_audit_trail": True,
        },

        # =========================
        # DEFAULT DECISION BASELINE
        # =========================
        "defaults": {
            "status": "APPROVED",
            "severity": "LOW",
            "risk_score": 0,
            "recommended_action": "RELEASE_BATCH",
            "decision_code": "PHARMA_APPROVED",
            "batch_disposition": "RELEASED",
        },

        # =========================
        # RULESET
        # =========================
        "rules": rules_data,
    }


def load_config():
    return get_pharma_config()
