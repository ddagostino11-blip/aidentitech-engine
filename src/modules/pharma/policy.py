def apply_policy(decision: dict, module_config: dict, payload: dict | None = None) -> dict:
    policy = module_config.get("policy", {})
    profile = policy.get("profile", "default")

    result = dict(decision)

    issues = result.get("issues", [])
    max_severity = result.get("severity", "LOW")

    if not issues:
        result["policy_profile"] = profile
        return result

    if profile == "strict":
        if max_severity == "MEDIUM":
            result["status"] = "REJECTED"
            result["recommended_action"] = "HOLD_BATCH"
            result["decision_code"] = "PHARMA_REJECTED_BY_POLICY"
            result["review_required"] = True
            result["regulatory_impact"] = "HIGH"
            result["batch_disposition"] = "QUARANTINED"

    elif profile == "regulated_high_risk":
        high_or_medium = [i for i in issues if i.get("severity") in ["HIGH", "MEDIUM"]]
        if high_or_medium:
            result["review_required"] = True
            if max_severity == "MEDIUM":
                result["status"] = "REJECTED"
                result["recommended_action"] = "HOLD_BATCH"
                result["decision_code"] = "PHARMA_REJECTED_BY_POLICY"
                result["regulatory_impact"] = "HIGH"
                result["batch_disposition"] = "QUARANTINED"

    elif profile == "lenient":
        only_medium = issues and all(i.get("severity") == "MEDIUM" for i in issues)
        if only_medium:
            result["status"] = "APPROVED"
            result["recommended_action"] = "RELEASE_BATCH"
            result["decision_code"] = "PHARMA_APPROVED_BY_POLICY"
            result["review_required"] = False
            result["regulatory_impact"] = "LOW"
            result["batch_disposition"] = "RELEASED"

    result["policy_profile"] = profile
    return result
