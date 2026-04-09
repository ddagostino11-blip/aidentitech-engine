import json
import hashlib
from pathlib import Path
from src.shared.regulatory_state import load_regulatory_state


def _compute_rules_hash(rules_data: dict) -> str:
    payload = json.dumps(rules_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_pharma_config():
    rules_path = Path(__file__).with_name("pharma_rules.json")

    with open(rules_path, "r", encoding="utf-8") as f:
        rules_data = json.load(f)

    rules_version = rules_data.get("rules_version", "pharma-v1.0.0")
    rules_hash = _compute_rules_hash(rules_data)

    # 🔥 LOAD REGULATORY STATE
    reg_state = load_regulatory_state().get("pharma", {})

    return {
        "module_name": "pharma",
        "dossier_type": "MASTER_PHARMA",

        # VERSIONING (ENGINE LEVEL)
        "engine_version": "1.0",
        "policy_version": "2.0",
        "rules_version": rules_version,
        "rules_hash": rules_hash,
        "ruleset_id": reg_state.get("ruleset_id", rules_version),
        "pipeline_id": "pharma-pipeline-004",

        # METADATA
        "metadata": {
            "domain": "pharma",
            "jurisdictions": ["EU", "US"],
            "authorities": ["EMA", "FDA"]
        },

        # REGULATORY CONTEXT (DYNAMIC)
        "regulatory_context": {
            "region": reg_state.get("region"),
            "authority": reg_state.get("authority"),
            "country": reg_state.get("country")
        },

        # 🔥 FREEZE FLAG (FONDAMENTALE)
        "freeze_active": reg_state.get("freeze_active", False),

        # COMPLIANCE SCOPE (INTERNAL IDS)
        "compliance_scope": {
            "frameworks": [
                "GMP",
                "ICH_Q9",
                "GCP",
                "ALCOA_PLUS"
            ],
            "criticality": "HIGH",
            "regulated": True,
            "requires_audit_trail": True
        },

        # OPTIONAL DISPLAY LABELS
        "framework_labels": {
            "GMP": "GMP",
            "ICH_Q9": "ICH Q9",
            "GCP": "GCP",
            "ALCOA_PLUS": "ALCOA+"
        },

        # VERSION BLOCK (AUDIT READY)
        "versioning": {
            "engine_version": "1.0",
            "policy_version": "2.0",
            "rules_version": rules_version,
            "rules_hash": rules_hash,
            "ruleset_id": reg_state.get("ruleset_id", rules_version)
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
