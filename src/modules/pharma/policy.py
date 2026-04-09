import json
from pathlib import Path

from src.shared.regulatory_state import (
    get_domain_state,
    get_freeze_metadata,
    is_domain_frozen,
)


def _load_impact_registry():
    try:
        path = Path("src/shared/impact_registry.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def apply_policy(decision: dict, module_config: dict, payload: dict | None = None) -> dict:
    if not isinstance(decision, dict):
        return decision or {}

    if not isinstance(module_config, dict):
        module_config = {}

    if payload is None:
        payload = {}
    elif not isinstance(payload, dict):
        payload = {}

    result = dict(decision)

    # =========================
    # LOAD EXTERNAL REGISTRIES
    # =========================
    impact_registry = _load_impact_registry()

    module_name = module_config.get("module_name", "pharma")
    module_state = get_domain_state(module_name)
    freeze_metadata = get_freeze_metadata(module_name)
    module_impacts = impact_registry.get(module_name, {})

    # =========================
    # REGULATORY CONTEXT
    # =========================
    payload_regulatory_context = payload.get("regulatory_context") or {}
    module_regulatory_context = module_config.get("regulatory_context") or {}
    regulatory_context = payload_regulatory_context or module_regulatory_context or {}

    region = regulatory_context.get("region", "UNKNOWN")
    authority = regulatory_context.get("authority", "UNKNOWN")

    # =========================
    # 🚨 CENTRALIZED RUNTIME FREEZE CHECK
    # =========================
    if is_domain_frozen(module_name):
        freeze_impact = module_impacts.get("REGULATORY_FREEZE", {})

        result.update({
            "status": "FROZEN",
            "severity": freeze_impact.get("severity", "CRITICAL"),
            "decision_code": "REGULATORY_FREEZE",
            "recommended_action": freeze_impact.get("recommended_action", "ESCALATE_IMMEDIATELY"),
            "regulatory_impact": "CRITICAL",
            "batch_disposition": "BLOCKED",
            "execution_allowed": freeze_impact.get("execution_allowed", False),
            "output_type": "REGULATORY_BLOCK",
            "review_required": True,
            "hard_block": True,
            "freeze_active": True,
            "freeze_reason": freeze_metadata.get("freeze_reason"),
            "freeze_timestamp": freeze_metadata.get("freeze_timestamp"),
            "triggered_by": freeze_metadata.get("triggered_by"),
        })

        result["issues"] = result.get("issues", [])
        result["issues"].append({
            "code": "REGULATORY_FREEZE",
            "severity": freeze_impact.get("severity", "CRITICAL"),
            "recommended_action": freeze_impact.get("recommended_action", "ESCALATE_IMMEDIATELY"),
            "details": "Module execution blocked by centralized Sentinel regulatory freeze."
        })

        result["policy_profile"] = "regulatory_override"
        result["regulatory_context"] = regulatory_context
        result["region"] = region
        result["authority"] = authority
        result["module_state"] = module_state

        return result

    # =========================
    # STANDARD POLICY LOGIC
    # =========================
    policy = module_config.get("policy", {})
    profile = policy.get("profile", "default")

    issues = result.get("issues", []) or []
    max_severity = result.get("severity", "LOW")

    if not issues:
        result["policy_profile"] = profile
        result["regulatory_context"] = regulatory_context
        result["region"] = region
        result["authority"] = authority
        result["module_state"] = module_state
        return result

    if profile == "strict":
        if max_severity in ["MEDIUM", "HIGH", "CRITICAL"]:
            result["status"] = "REJECTED"
            result["recommended_action"] = "HOLD_BATCH"
            result["decision_code"] = "PHARMA_REJECTED_BY_POLICY"
            result["review_required"] = True
            result["regulatory_impact"] = "HIGH"
            result["batch_disposition"] = "QUARANTINED"

    elif profile == "regulated_high_risk":
        high_or_medium = [
            i for i in issues
            if isinstance(i, dict) and i.get("severity") in ["MEDIUM", "HIGH", "CRITICAL"]
        ]

        if high_or_medium:
            result["review_required"] = True

            if max_severity in ["MEDIUM", "HIGH", "CRITICAL"]:
                result["status"] = "REJECTED"
                result["recommended_action"] = "HOLD_BATCH"
                result["decision_code"] = "PHARMA_REJECTED_BY_POLICY"
                result["regulatory_impact"] = "HIGH"
                result["batch_disposition"] = "QUARANTINED"

    elif profile == "lenient":
        only_medium = issues and all(
            isinstance(i, dict) and i.get("severity") == "MEDIUM"
            for i in issues
        )

        if only_medium:
            result["status"] = "APPROVED"
            result["recommended_action"] = "RELEASE_BATCH"
            result["decision_code"] = "PHARMA_APPROVED_BY_POLICY"
            result["review_required"] = False
            result["regulatory_impact"] = "LOW"
            result["batch_disposition"] = "RELEASED"

    # =========================
    # FINAL METADATA
    # =========================
    result["policy_profile"] = profile
    result["regulatory_context"] = regulatory_context
    result["region"] = region
    result["authority"] = authority
    result["module_state"] = module_state
    result["freeze_active"] = False

    return result