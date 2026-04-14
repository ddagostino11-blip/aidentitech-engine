REGULATORY_IMPACT_MAP = {
    "LOW": "LOW",
    "MEDIUM": "MEDIUM",
    "HIGH": "HIGH",
    "CRITICAL": "HIGH",
}


POLICY_ACTIONS = {
    "high_risk_review": {
        "decision_code": "PHARMA_HIGH_RISK_REVIEW",
        "recommended_action": "QUALITY_REVIEW",
        "batch_disposition": "QUARANTINED",
        "review_required": True,
        "status_if_approved": "REVIEW",
    },
    "rejected_by_policy": {
        "decision_code": "PHARMA_REJECTED_BY_POLICY",
        "recommended_action": "HOLD_BATCH",
        "batch_disposition": "QUARANTINED",
        "review_required": True,
        "status": "REJECTED",
    },
    "lenient_review": {
        "decision_code": "PHARMA_LENIENT_REVIEW",
        "recommended_action": "QUALITY_REVIEW",
        "batch_disposition": "ON_HOLD",
        "review_required": True,
        "status": "REVIEW",
    },
}


def _regulatory_impact_from_severity(severity: str) -> str:
    return REGULATORY_IMPACT_MAP.get(severity, "LOW")


def _apply_action(result: dict, action_key: str):
    action = POLICY_ACTIONS[action_key]

    if "status" in action:
        result["status"] = action["status"]

    if action.get("status_if_approved") and result.get("status") == "APPROVED":
        result["status"] = action["status_if_approved"]

    result["decision_code"] = action["decision_code"]
    result["recommended_action"] = action["recommended_action"]
    result["batch_disposition"] = action["batch_disposition"]
    result["review_required"] = action["review_required"]


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
        _apply_action(result, "high_risk_review")

    if profile == "strict":
        if max_severity == "MEDIUM":
            _apply_action(result, "rejected_by_policy")

    elif profile == "regulated_high_risk":
        relevant_issues = [
            issue for issue in issues
            if issue.get("severity") in {"HIGH", "MEDIUM"}
        ]
        if relevant_issues:
            result["review_required"] = True

            if max_severity == "MEDIUM":
                _apply_action(result, "rejected_by_policy")

    elif profile == "lenient":
        only_medium = issues and all(issue.get("severity") == "MEDIUM" for issue in issues)
        if only_medium:
            _apply_action(result, "lenient_review")

    final_severity = result.get("severity", max_severity)
    result["regulatory_impact"] = _regulatory_impact_from_severity(final_severity)

    return result
