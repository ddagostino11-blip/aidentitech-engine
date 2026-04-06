from typing import List, Dict, Any


def evaluate_rules(payload: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues = []
    audit = []

    max_severity = "LOW"
    status = "APPROVED"
    recommended_action = "RELEASE_BATCH"

    severity_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

    for rule in rules:
        rule_id = rule.get("rule_id")
        rule_type = rule.get("rule_type")
        field = rule.get("field")

        actual_value = payload.get(field)

        outcome = "passed"
        triggered = False

        if rule_type == "required_field":
            if actual_value is None:
                outcome = "failed"
                triggered = True

        elif rule_type == "numeric_gt":
            if actual_value is not None and actual_value > rule.get("expected"):
                outcome = "triggered"
                triggered = True

        elif rule_type == "numeric_lt":
            if actual_value is not None and actual_value < rule.get("expected"):
                outcome = "triggered"
                triggered = True

        elif rule_type == "boolean_equals":
            if actual_value == rule.get("expected"):
                outcome = "triggered"
                triggered = True

        audit.append({
            "rule_id": rule_id,
            "rule_type": rule_type,
            "field": field,
            "actual_value": actual_value,
            "expected": rule.get("expected"),
            "outcome": outcome
        })

        if triggered:
            severity = rule.get("severity", "LOW")

            issues.append({
                "code": rule_id,
                "field": field,
                "actual_value": actual_value,
                "threshold": rule.get("expected"),
                "severity": severity,
                "recommended_action": rule.get("action", "REVIEW")
            })

            # aggiorna severità massima
            if severity_order.get(severity, 1) > severity_order.get(max_severity, 1):
                max_severity = severity

    # decision logic finale
    if max_severity == "LOW":
        status = "APPROVED"
        recommended_action = "RELEASE_BATCH"
    elif max_severity == "MEDIUM":
        status = "WARNING"
        recommended_action = "QUALITY_REVIEW"
    elif max_severity == "HIGH":
        status = "CRITICAL"
        recommended_action = "BLOCK_BATCH"

    result = {
        "status": status,
        "severity": max_severity,
        "issues": issues,
        "audit": audit,
        "recommended_action": recommended_action
    }

    return result
