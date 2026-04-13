def _regulatory_impact_from_severity(severity: str) -> str:
    mapping = {
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "HIGH",
    }
    return mapping.get(severity, "LOW")


def apply_policy(decision: dict, module_config: dict, payload: dict | None = None) -> dict:
    policy = module_config.get("policy", {})
    profile = policy.get("profile", "default")

    result = dict(decision)

    issues = result.get("issues", [])
    max_severity = result.get("severity", "LOW")
    risk_score = result.get("risk_score", 0)

    result["policy_profile"] = profile

    if not issues:
        result["regulatory_impact"] = _regulatory_impact_from_severity(max_severity)
        return result

    # Operational risk can harden handling, but must not alter severity/regulatory truth.
    if max_severity == "MEDIUM" and risk_score >= 80:
        result["decision_code"] = "PHARMA_HIGH_RISK_REVIEW"
        result["recommended_action"] = "QUALITY_REVIEW"
        result["batch_disposition"] = "QUARANTINED"
        result["review_required"] = True

        if result.get("status") == "APPROVED":
            result["status"] = "REVIEW"

    if profile == "strict":
        if max_severity == "MEDIUM":
            result["status"] = "REJECTED"
            result["recommended_action"] = "HOLD_BATCH"
            result["decision_code"] = "PHARMA_REJECTED_BY_POLICY"
            result["review_required"] = True
            result["batch_disposition"] = "QUARANTINED"

    elif profile == "regulated_high_risk":
        relevant_issues = [
            issue for issue in issues
            if issue.get("severity") in {"HIGH", "MEDIUM"}
        ]
        if relevant_issues:
            result["review_required"] = True

            if max_severity == "MEDIUM":
                result["status"] = "REJECTED"
                result["recommended_action"] = "HOLD_BATCH"
                result["decision_code"] = "PHARMA_REJECTED_BY_POLICY"
                result["batch_disposition"] = "QUARANTINED"

    elif profile == "lenient":
        only_medium = issues and all(issue.get("severity") == "MEDIUM" for issue in issues)
        if only_medium:
            result["status"] = "REVIEW"
            result["recommended_action"] = "QUALITY_REVIEW"
            result["decision_code"] = "PHARMA_LENIENT_REVIEW"
            result["review_required"] = True
            result["batch_disposition"] = "ON_HOLD"

    final_severity = result.get("severity", max_severity)
    result["regulatory_impact"] = _regulatory_impact_from_severity(final_severity)

    return result
