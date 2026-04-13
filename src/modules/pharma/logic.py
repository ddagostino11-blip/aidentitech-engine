from src.core.rule_engine import evaluate_rules
from src.core.explainer import build_explanation
from src.modules.pharma.policy import apply_policy


def _normalize_pharma_rules(module_config: dict) -> list:
    rules = module_config.get("rules", {})
    normalized_rules = []

    for field in rules.get("required_fields", []):
        normalized_rules.append(
            {
                "rule_id": f"required_{field}",
                "rule_type": "required_field",
                "field": field,
                "group": f"required_{field}",
                "priority": 200,
                "severity": "HIGH",
                "recommended_action": "HOLD_BATCH",
                "status": "REJECTED",
                "risk_score": 0,
                "issue_code": f"required_{field}",
            }
        )

    for rule in rules.get("checks", []):
        normalized_rules.append(
            {
                "rule_id": rule.get("rule_id"),
                "rule_type": "comparison_rule",
                "field": rule.get("field"),
                "group": rule.get("group"),
                "priority": rule.get("priority", 0),
                "operator": rule.get("operator"),
                "violation_value": rule.get("violation_value"),
                "threshold": rule.get("threshold"),
                "min_inclusive": rule.get("min_inclusive"),
                "max_inclusive": rule.get("max_inclusive"),
                "min_exclusive": rule.get("min_exclusive"),
                "max_exclusive": rule.get("max_exclusive"),
                "severity": rule.get("severity", "LOW"),
                "recommended_action": rule.get("recommended_action", "RELEASE_BATCH"),
                "status": rule.get("status", "APPROVED"),
                "risk_score": rule.get("risk_score", 0),
                "issue_code": rule.get("issue_code", rule.get("rule_id")),
            }
        )

    return normalized_rules


def _regulatory_impact_from_severity(severity: str) -> str:
    mapping = {
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "HIGH",
    }
    return mapping.get(severity, "LOW")


def _normalize_issue(issue: dict, action_map: dict) -> dict:
    raw_action = issue.get("recommended_action", "RELEASE_BATCH")

    return {
        "code": issue.get("code"),
        "field": issue.get("field"),
        "actual_value": issue.get("actual_value"),
        "group": issue.get("group"),
        "priority": issue.get("priority"),
        "operator": issue.get("operator"),
        "violation_value": issue.get("violation_value"),
        "threshold": issue.get("threshold"),
        "min_inclusive": issue.get("min_inclusive"),
        "max_inclusive": issue.get("max_inclusive"),
        "min_exclusive": issue.get("min_exclusive"),
        "max_exclusive": issue.get("max_exclusive"),
        "severity": issue.get("severity", "LOW"),
        "recommended_action": action_map.get(raw_action, raw_action),
        "risk_score": issue.get("risk_score", 0),
        "status": issue.get("status"),
        "rule_id": issue.get("rule_id"),
        "rule_type": issue.get("rule_type"),
    }


def _apply_decision_guardrails(result: dict, max_severity: str) -> dict:
    if max_severity == "HIGH":
        result["status"] = "REJECTED"
        result["recommended_action"] = "HOLD_BATCH"
        result["decision_code"] = "PHARMA_HIGH_RISK_REJECT"
        result["review_required"] = True
        result["batch_disposition"] = "QUARANTINED"
        result["regulatory_impact"] = _regulatory_impact_from_severity(max_severity)

    elif max_severity == "CRITICAL":
        result["status"] = "CRITICAL"
        result["recommended_action"] = "BLOCK_AND_ESCALATE"
        result["decision_code"] = "PHARMA_CRITICAL_REJECT"
        result["review_required"] = True
        result["batch_disposition"] = "BLOCKED"
        result["regulatory_impact"] = _regulatory_impact_from_severity(max_severity)

    if result.get("status") == "APPROVED" and max_severity in {"MEDIUM", "HIGH", "CRITICAL"}:
        result["status"] = "REVIEW"
        result["recommended_action"] = "QUALITY_REVIEW"
        result["review_required"] = True

        if not result.get("decision_code"):
            result["decision_code"] = "PHARMA_REVIEW_REQUIRED"

        if not result.get("batch_disposition"):
            result["batch_disposition"] = "ON_HOLD"

        result["regulatory_impact"] = _regulatory_impact_from_severity(max_severity)

    return result


def run(module_config: dict, payload: dict):
    normalized_rules = _normalize_pharma_rules(module_config)
    compliance_scope = module_config.get("compliance_scope", {})
    action_map = module_config.get("rules", {}).get("actions", {})

    engine_result = evaluate_rules(payload, normalized_rules)
    engine_issues = engine_result.get("issues", [])

    normalized_issues = [
        _normalize_issue(issue, action_map)
        for issue in engine_issues
    ]

    primary_issue_raw = engine_result.get("primary_issue")
    primary_issue = (
        _normalize_issue(primary_issue_raw, action_map)
        if primary_issue_raw
        else None
    )

    result = {
        "status": "APPROVED",
        "risk_score": engine_result.get("risk_score", 0),
        "issues": normalized_issues,
        "primary_issue": primary_issue,
        "audit": engine_result.get("audit", []),
        "severity": engine_result.get("severity", "LOW"),
        "recommended_action": "RELEASE_BATCH",
        "compliance_scope": compliance_scope,
        "review_required": False,
        "blocking_issues_count": 0,
        "decision_code": "PHARMA_APPROVED",
        "regulatory_impact": "LOW",
        "batch_disposition": "RELEASED",
    }

    max_severity = result["severity"]

    blocking_issues = [
        issue for issue in result["issues"]
        if issue.get("severity") in {"HIGH", "CRITICAL"}
    ]
    medium_issues = [
        issue for issue in result["issues"]
        if issue.get("severity") == "MEDIUM"
    ]

    result["blocking_issues_count"] = len(blocking_issues)
    result["regulatory_impact"] = _regulatory_impact_from_severity(max_severity)

    if max_severity == "CRITICAL":
        result["status"] = "CRITICAL"
        result["recommended_action"] = "BLOCK_AND_ESCALATE"
        result["decision_code"] = "PHARMA_CRITICAL_REJECT"
        result["review_required"] = True
        result["batch_disposition"] = "BLOCKED"

    elif max_severity == "HIGH":
        result["status"] = "REJECTED"
        result["recommended_action"] = "HOLD_BATCH"
        result["decision_code"] = "PHARMA_HIGH_RISK_REJECT"
        result["review_required"] = True
        result["batch_disposition"] = "QUARANTINED"

    elif max_severity == "MEDIUM":
        result["status"] = "REVIEW"
        result["recommended_action"] = "QUALITY_REVIEW"
        result["review_required"] = True
        result["decision_code"] = "PHARMA_WARNING"
        result["batch_disposition"] = "ON_HOLD"

        if result["risk_score"] >= 75:
            result["decision_code"] = "PHARMA_HIGH_RISK_REVIEW"
            result["batch_disposition"] = "QUARANTINED"
        elif len(medium_issues) >= 2:
            result["decision_code"] = "PHARMA_MULTI_WARNING"
            result["batch_disposition"] = "QUARANTINED"

    else:
        result["status"] = "APPROVED"
        result["recommended_action"] = "RELEASE_BATCH"
        result["decision_code"] = "PHARMA_APPROVED"
        result["review_required"] = False
        result["batch_disposition"] = "RELEASED"

    if primary_issue and max_severity in {"HIGH", "CRITICAL"}:
        result["recommended_action"] = primary_issue.get(
            "recommended_action",
            result["recommended_action"],
        )

    result = apply_policy(result, module_config, payload)
    result = _apply_decision_guardrails(result, max_severity)
    result["explanation"] = build_explanation(result)

    return result
