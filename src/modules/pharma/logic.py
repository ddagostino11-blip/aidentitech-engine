from src.core.rule_engine import evaluate_rules
from src.core.explainer import build_explanation
from src.modules.pharma.policy import apply_policy


def _normalize_pharma_rules(module_config: dict) -> list:
    rules = module_config.get("rules", {})

    normalized_rules = []

    # Required fields
    for field in rules.get("required_fields", []):
        normalized_rules.append({
            "rule_id": f"required_{field}",
            "rule_type": "required_field",
            "field": field,
            "expected": "required",
            "severity": "HIGH",
            "recommended_action": "HOLD_BATCH"
        })

    # Checks
    for rule in rules.get("checks", []):
        normalized_rules.append({
            "rule_id": rule.get("rule_id"),
            "rule_type": rule.get("type"),
            "field": rule.get("field"),
            "expected": rule.get("threshold", rule.get("expected")),
            "severity": rule.get("severity", "LOW"),
            "recommended_action": rule.get("recommended_action", "RELEASE_BATCH"),
            "status": rule.get("status", "APPROVED"),
            "risk_score": rule.get("risk_score", 0),
            "issue_code": rule.get("issue_code", rule.get("rule_id"))
        })

    return normalized_rules


def _severity_rank(severity: str) -> int:
    ranking = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4
    }
    return ranking.get(severity, 0)


def run(module_config: dict, payload: dict):
    normalized_rules = _normalize_pharma_rules(module_config)
    compliance_scope = module_config.get("compliance_scope", {})
    action_map = module_config.get("rules", {}).get("actions", {})

    engine_result = evaluate_rules(payload, normalized_rules)

    result = {
        "status": "APPROVED",
        "risk_score": 0,
        "issues": [],
        "audit": engine_result.get("audit", []),
        "severity": "LOW",
        "recommended_action": "RELEASE_BATCH",
        "compliance_scope": compliance_scope,
    }

    # Normalize issues
    for issue in engine_result.get("issues", []):
        raw_action = issue.get("recommended_action", "RELEASE_BATCH")
        normalized_issue = {
            "code": issue.get("code"),
            "field": issue.get("field"),
            "actual_value": issue.get("actual_value"),
            "threshold": issue.get("threshold"),
            "severity": issue.get("severity", "LOW"),
            "recommended_action": action_map.get(raw_action, raw_action),
            "risk_score": issue.get("risk_score", 0),
            "status": issue.get("status")
        }

        result["issues"].append(normalized_issue)
        result["risk_score"] += issue.get("risk_score", 0)

    # Aggregation
    if result["issues"]:
        max_severity = max(
            result["issues"],
            key=lambda x: _severity_rank(x.get("severity", "LOW"))
        )["severity"]
    else:
        max_severity = "LOW"

    result["severity"] = max_severity

    blocking_issues = [
        i for i in result["issues"] if i.get("severity") in ["HIGH", "CRITICAL"]
    ]
    medium_issues = [
        i for i in result["issues"] if i.get("severity") == "MEDIUM"
    ]

    result["blocking_issues_count"] = len(blocking_issues)

    # Enterprise decision logic
    if max_severity == "CRITICAL":
        result["status"] = "REJECTED"
        result["recommended_action"] = "BLOCK_AND_ESCALATE"
        result["decision_code"] = "PHARMA_CRITICAL"
        result["review_required"] = True
        result["regulatory_impact"] = "HIGH"
        result["batch_disposition"] = "BLOCKED"

    elif max_severity == "HIGH":
        result["status"] = "REJECTED"
        result["recommended_action"] = "HOLD_BATCH"
        result["decision_code"] = "PHARMA_REJECTED"
        result["review_required"] = True
        result["regulatory_impact"] = "HIGH"
        result["batch_disposition"] = "QUARANTINED"

    elif max_severity == "MEDIUM":
        result["status"] = "REVIEW"
        result["recommended_action"] = "QUALITY_REVIEW"
        result["decision_code"] = "PHARMA_WARNING"
        result["review_required"] = True
        result["regulatory_impact"] = "MEDIUM"
        result["batch_disposition"] = "ON_HOLD"

        # Multi-issue escalation
        if len(medium_issues) >= 2:
            result["decision_code"] = "PHARMA_MULTI_WARNING"
            result["regulatory_impact"] = "HIGH"
            result["batch_disposition"] = "QUARANTINED"

        # Risk-based escalation within review state
        if result["risk_score"] >= 50:
            result["decision_code"] = "PHARMA_HIGH_RISK_REVIEW"
            result["regulatory_impact"] = "HIGH"
            result["batch_disposition"] = "QUARANTINED"

    else:
        result["status"] = "APPROVED"
        result["recommended_action"] = "RELEASE_BATCH"
        result["decision_code"] = "PHARMA_APPROVED"
        result["review_required"] = False
        result["regulatory_impact"] = "LOW"
        result["batch_disposition"] = "RELEASED"

    # Explanation + payload
    result["explanation"] = build_explanation(result)
    result["payload_received"] = payload

    # Policy layer
    result = apply_policy(result, module_config, payload)

    return result
