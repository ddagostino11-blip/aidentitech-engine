def apply_policy(decision: dict, module_config: dict, payload: dict | None = None) -> dict:
    if not isinstance(decision, dict):
        return decision or {}

    if not isinstance(module_config, dict):
        module_config = {}

    if payload is not None and not isinstance(payload, dict):
        payload = {}

    policy = module_config.get("policy", {})
    profile = policy.get("profile", "default")

    result = dict(decision)

    issues = result.get("issues", []) or []
    max_severity = result.get("severity", "LOW")

    payload_regulatory_context = {}
    if isinstance(payload, dict):
        payload_regulatory_context = payload.get("regulatory_context") or {}

    module_regulatory_context = module_config.get("regulatory_context") or {}

    regulatory_context = payload_regulatory_context or module_regulatory_context or {}

    region = regulatory_context.get("region", "UNKNOWN")
    authority = regulatory_context.get("authority", "UNKNOWN")

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

    result["policy_profile"] = profile
    result["regulatory_context"] = regulatory_context
    result["region"] = region
    result["authority"] = authority

    return result
