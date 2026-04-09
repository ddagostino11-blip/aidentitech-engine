import json
from pathlib import Path


def _load_impact_registry():
    try:
        path = Path("src/shared/impact_registry.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_regulatory_state():
    try:
        path = Path("src/shared/regulatory_state.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def apply_policy(decision: dict, module_config: dict, payload: dict | None = None) -> dict:
    if not isinstance(decision, dict):
        return decision or {}

    if not isinstance(module_config, dict):
        module_config = {}

    if payload is not None and not isinstance(payload, dict):
        payload = {}

    result = dict(decision)

    # =========================
    # LOAD EXTERNAL REGISTRIES
    # =========================
    impact_registry = _load_impact_registry()
    regulatory_state = _load_regulatory_state()

    module_name = module_config.get("module_name", "pharma")

    module_state = regulatory_state.get(module_name, {})
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
    # 🚨 REGULATORY FREEZE CHECK
    # =========================
    if module_state.get("freeze_active") is True:
        freeze_impact = module_impacts.get("REGULATORY_FREEZE", {})

        result.update({
            "status": "FROZEN",
            "severity": freeze_impact.get("severity", "CRITICAL"),
            "decision_code": "REGULATORY_FREEZE",
            "recommended_action": freeze_impact.get("recommended_action", "ESCALATE"),
            "regulatory_impact": "CRITICAL",
            "batch_disposition": "BLOCKED",
            "execution_allowed": freeze_impact.get("execution_allowed", False),
            "output_type": "REGULATORY_BLOCK",
            "review_required": True
        })

        result["policy_profile"] = "regulatory_override"
        result["regulatory_context"] = regulatory_context
        result["region"] = region
        result["authority"] = authority

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

    return result
