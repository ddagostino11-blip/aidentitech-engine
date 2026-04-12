from typing import List, Dict, Any


def evaluate_rules(payload: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues = []
    audit = []

    max_severity = "LOW"
    total_risk_score = 0

    severity_order = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4
    }

    for rule in rules:
        rule_id = rule.get("rule_id")
        rule_type = rule.get("rule_type")
        field = rule.get("field")

        actual_value = payload.get(field)
        expected_value = rule.get("expected")

        outcome = "passed"
        triggered = False

        if rule_type == "required_field":
            if actual_value is None:
                outcome = "failed"
                triggered = True

        elif rule_type == "numeric_gt":
            if actual_value is not None and expected_value is not None and actual_value > expected_value:
                outcome = "triggered"
                triggered = True

        elif rule_type == "numeric_lt":
            if actual_value is not None and expected_value is not None and actual_value < expected_value:
                outcome = "triggered"
                triggered = True

        elif rule_type == "boolean_equals":
            if actual_value == expected_value:
                outcome = "triggered"
                triggered = True

        audit.append({
            "rule_id": rule_id,
            "rule_type": rule_type,
            "field": field,
            "actual_value": actual_value,
            "expected": expected_value,
            "outcome": outcome
        })

        if triggered:
            severity = rule.get("severity", "LOW")
            risk_score = rule.get("risk_score", 0)
            recommended_action = rule.get("recommended_action", "QUALITY_REVIEW")
            issue_code = rule.get("issue_code", rule_id)
            issue_status = rule.get("status", "APPROVED")

            issues.append({
                "code": issue_code,
                "field": field,
                "actual_value": actual_value,
                "threshold": expected_value,
                "severity": severity,
                "recommended_action": recommended_action,
                "risk_score": risk_score,
                "status": issue_status
            })

            total_risk_score += risk_score

            if severity_order.get(severity, 1) > severity_order.get(max_severity, 1):
                max_severity = severity

    # decision logic finale, coerente con la tua architettura attuale
    if max_severity == "CRITICAL":
        status = "CRITICAL"
        recommended_action = "BLOCK_AND_ESCALATE"
    elif max_severity == "HIGH":
        status = "REJECTED"
        recommended_action = "HOLD_BATCH"
    elif max_severity == "MEDIUM":
        status = "REVIEW"
        recommended_action = "QUALITY_REVIEW"
    else:
        status = "APPROVED"
        recommended_action = "RELEASE_BATCH"

    result = {
        "status": status,
        "severity": max_severity,
        "risk_score": total_risk_score,
        "issues": issues,
        "audit": audit,
        "recommended_action": recommended_action
    }

    return result
