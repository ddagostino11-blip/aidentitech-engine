from src.core.explainer import build_explanation


def _severity_rank(severity: str) -> int:
    ranking = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4
    }
    return ranking.get(severity, 0)


def _status_rank(status: str) -> int:
    ranking = {
        "APPROVED": 1,
        "WARNING": 2,
        "REJECTED": 3,
        "CRITICAL": 4
    }
    return ranking.get(status, 0)


def _update_decision(result: dict, status: str, severity: str, action: str):
    if _status_rank(status) > _status_rank(result["status"]):
        result["status"] = status

    if _severity_rank(severity) > _severity_rank(result["severity"]):
        result["severity"] = severity

    actions_priority = {
        "RELEASE_BATCH": 1,
        "QUALITY_REVIEW": 2,
        "HOLD_BATCH": 3,
        "BLOCK_AND_ESCALATE": 4
    }

    current_action = result.get("recommended_action")
    if actions_priority.get(action, 0) > actions_priority.get(current_action, 0):
        result["recommended_action"] = action


def _check_required_fields(rules: dict, payload: dict, result: dict, audit: list):
    required_fields = rules.get("required_fields", [])

    for field in required_fields:
        value = payload.get(field)

        if field not in payload or value is None:
            result["issues"].append({
                "code": f"missing_{field}",
                "field": field,
                "actual_value": value,
                "severity": "HIGH"
            })
            result["risk_score"] += 25

            audit.append({
                "rule_id": f"required_{field}",
                "rule_type": "required_field",
                "field": field,
                "actual_value": value,
                "expected": "required",
                "outcome": "failed"
            })

            _update_decision(
                result,
                status="REJECTED",
                severity="HIGH",
                action="HOLD_BATCH"
            )
        else:
            audit.append({
                "rule_id": f"required_{field}",
                "rule_type": "required_field",
                "field": field,
                "actual_value": value,
                "expected": "required",
                "outcome": "passed"
            })


def _check_boolean_equals(rule: dict, payload: dict, result: dict, audit: list):
    field = rule.get("field")
    expected = rule.get("expected")
    value = payload.get(field)

    if field not in payload:
        return

    if value == expected:
        result["issues"].append({
            "code": rule.get("issue_code"),
            "field": field,
            "actual_value": value,
            "severity": rule.get("severity", "MEDIUM")
        })
        result["risk_score"] += rule.get("risk_score", 0)

        audit.append({
            "rule_id": rule.get("issue_code"),
            "rule_type": "boolean_equals",
            "field": field,
            "actual_value": value,
            "expected": expected,
            "outcome": "triggered"
        })

        _update_decision(
            result,
            status=rule.get("status", "WARNING"),
            severity=rule.get("severity", "MEDIUM"),
            action=rule.get("recommended_action", "QUALITY_REVIEW")
        )
    else:
        audit.append({
            "rule_id": rule.get("issue_code"),
            "rule_type": "boolean_equals",
            "field": field,
            "actual_value": value,
            "expected": expected,
            "outcome": "passed"
        })


def _check_numeric_gt(rule: dict, payload: dict, result: dict, audit: list):
    field = rule.get("field")
    threshold = rule.get("threshold")
    value = payload.get(field)

    if field not in payload or value is None:
        return

    if value > threshold:
        result["issues"].append({
            "code": rule.get("issue_code"),
            "field": field,
            "actual_value": value,
            "threshold": threshold,
            "severity": rule.get("severity", "MEDIUM")
        })
        result["risk_score"] += rule.get("risk_score", 0)

        audit.append({
            "rule_id": rule.get("issue_code"),
            "rule_type": "numeric_gt",
            "field": field,
            "actual_value": value,
            "expected": threshold,
            "outcome": "triggered"
        })

        _update_decision(
            result,
            status=rule.get("status", "WARNING"),
            severity=rule.get("severity", "MEDIUM"),
            action=rule.get("recommended_action", "QUALITY_REVIEW")
        )
    else:
        audit.append({
            "rule_id": rule.get("issue_code"),
            "rule_type": "numeric_gt",
            "field": field,
            "actual_value": value,
            "expected": threshold,
            "outcome": "passed"
        })


def _check_numeric_lt(rule: dict, payload: dict, result: dict, audit: list):
    field = rule.get("field")
    threshold = rule.get("threshold")
    value = payload.get(field)

    if field not in payload or value is None:
        return

    if value < threshold:
        result["issues"].append({
            "code": rule.get("issue_code"),
            "field": field,
            "actual_value": value,
            "threshold": threshold,
            "severity": rule.get("severity", "MEDIUM")
        })
        result["risk_score"] += rule.get("risk_score", 0)

        audit.append({
            "rule_id": rule.get("issue_code"),
            "rule_type": "numeric_lt",
            "field": field,
            "actual_value": value,
            "expected": threshold,
            "outcome": "triggered"
        })

        _update_decision(
            result,
            status=rule.get("status", "WARNING"),
            severity=rule.get("severity", "MEDIUM"),
            action=rule.get("recommended_action", "QUALITY_REVIEW")
        )
    else:
        audit.append({
            "rule_id": rule.get("issue_code"),
            "rule_type": "numeric_lt",
            "field": field,
            "actual_value": value,
            "expected": threshold,
            "outcome": "passed"
        })


def run(module_config: dict, payload: dict):
    rules = module_config.get("rules", {})
    actions = rules.get("actions", {})

    result = {
        "status": "APPROVED",
        "risk_score": 0,
        "issues": [],
        "severity": "LOW",
        "recommended_action": actions.get("APPROVED", "RELEASE_BATCH")
    }

    audit = []

    _check_required_fields(rules, payload, result, audit)

    checks = rules.get("checks", [])
    for rule in checks:
        rule_type = rule.get("type")

        if rule_type == "boolean_equals":
            _check_boolean_equals(rule, payload, result, audit)
        elif rule_type == "numeric_gt":
            _check_numeric_gt(rule, payload, result, audit)
        elif rule_type == "numeric_lt":
            _check_numeric_lt(rule, payload, result, audit)

    result["audit"] = audit

    # 🔥 QUI IL COLLEGAMENTO AL CORE
    result["explanation"] = build_explanation(result)

    return result
