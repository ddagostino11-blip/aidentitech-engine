def apply_policy(decision: dict, module_config: dict, payload: dict | None = None) -> dict:
    policy = module_config.get("policy", {})
    profile = policy.get("profile", "default")

    result = dict(decision)

    issues = result.get("issues", [])
    max_severity = result.get("severity", "LOW")
    risk_score = result.get("risk_score", 0)

    if not issues:
        result["policy_profile"] = profile

        if max_severity == "LOW":
            result["regulatory_impact"] = "LOW"
        elif max_severity == "MEDIUM":
            result["regulatory_impact"] = "MEDIUM"
        elif max_severity in ["HIGH", "CRITICAL"]:
            result["regulatory_impact"] = "HIGH"

        return result

    # Base enterprise override:
    # il rischio operativo alto può irrigidire la gestione del caso,
    # ma NON deve alterare la verità regolatoria derivata dalla severity.
    if max_severity == "MEDIUM" and risk_score >= 80:
        result["decision_code"] = "PHARMA_HIGH_RISK_REVIEW"
        result["recommended_action"] = "QUALITY_REVIEW"
        result["batch_disposition"] = "QUARANTINED"
        result["review_required"] = True

    if profile == "strict":
        if max_severity == "MEDIUM":
            result["status"] = "REJECTED"
            result["recommended_action"] = "HOLD_BATCH"
            result["decision_code"] = "PHARMA_REJECTED_BY_POLICY"
            result["review_required"] = True
            result["batch_disposition"] = "QUARANTINED"

    elif profile == "regulated_high_risk":
        high_or_medium = [i for i in issues if i.get("severity") in ["HIGH", "MEDIUM"]]
        if high_or_medium:
            result["review_required"] = True
            if max_severity == "MEDIUM":
                result["status"] = "REJECTED"
                result["recommended_action"] = "HOLD_BATCH"
                result["decision_code"] = "PHARMA_REJECTED_BY_POLICY"
                result["batch_disposition"] = "QUARANTINED"

    elif profile == "lenient":
        only_medium = issues and all(i.get("severity") == "MEDIUM" for i in issues)
        if only_medium:
            result["status"] = "APPROVED"
            result["recommended_action"] = "RELEASE_BATCH"
            result["decision_code"] = "PHARMA_APPROVED_BY_POLICY"
            result["review_required"] = False
            result["batch_disposition"] = "RELEASED"

    # Consistency guard:
    # regulatory impact dipende dalla severity finale, non dal risk_score.
    final_severity = result.get("severity", max_severity)

    if final_severity == "LOW":
        result["regulatory_impact"] = "LOW"
    elif final_severity == "MEDIUM":
        result["regulatory_impact"] = "MEDIUM"
    elif final_severity in ["HIGH", "CRITICAL"]:
        result["regulatory_impact"] = "HIGH"

    result["policy_profile"] = profile
    return result
