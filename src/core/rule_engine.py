from typing import List, Dict, Any


def evaluate_rules(payload: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues = []
    audit = []

    result = {
        "status": "APPROVED",
        "severity": "LOW",
        "issues": [],
        "audit": [],
        "recommended_action": "RELEASE_BATCH"
    }

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
            issues.append({
                "code": rule_id,
                "field": field,
                "actual_value": actual_value,
                "threshold": rule.get("expected"),
                "severity": rule.get("severity", "LOW")
            })

    result["issues"] = issues
    result["audit"] = audit

    return result
