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


def _build_issue(
    code: str,
    field: str,
    severity: str,
    recommended_action: str,
    actual_value=None,
    threshold=None
) -> dict:
    return {
        "code": code,
        "field": field,
        "actual_value": actual_value,
        "threshold": threshold,
        "severity": severity,
        "recommended_action": recommended_action
    }


def _add_audit(
    result: dict,
    rule_id: str,
    rule_type: str,
    field: str,
    actual_value,
    expected,
    outcome: str
):
    result["audit"].append({
        "rule_id": rule_id,
        "rule_type": rule_type,
        "field": field,
        "actual_value": actual_value,
        "expected": expected,
        "outcome": outcome
    })


def _check_required_fields(rules: dict, payload: dict, result: dict):
    required_fields = rules.get("required_fields", [])

    for field in required_fields:
        actual_value = payload.get(field)

        if field not in payload or actual_value is None:
            result["issues"].append(
                _build_issue(
                    code=f"missing_{field}",
                    field=field,
                    actual_value=actual_value,
                    threshold="required",
                    severity="HIGH",
                    recommended_action="HOLD_BATCH"
                )
            )
            result["risk_score"] += 25
            _update_decision(
                result,
                status="REJECTED",
                severity="HIGH",
                action="HOLD_BATCH"
            )
            _add_audit(
                result,
                rule_id=f"required_{field}",
                rule_type="required_field",
                field=field,
                actual_value=actual_value,
                expected="required",
                outcome="triggered"
            )
        else:
            _add_audit(
                result,
                rule_id=f"required_{field}",
                rule_type="required_field",
                field=field,
                actual_value=actual_value,
                expected="required",
                outcome="passed"
            )


def _check_boolean_equals(rule: dict, payload: dict, result: dict):
    field = rule.get("field")
    expected = rule.get("expected")
    rule_id = rule.get("rule_id", "unknown_rule")
    actual_value = payload.get(field)

    if field not in payload:
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="boolean_equals",
            field=field,
            actual_value=None,
            expected=expected,
            outcome="skipped_missing_field"
        )
        return

    if actual_value == expected:
        result["issues"].append(
            _build_issue(
                code=rule.get("issue_code"),
                field=field,
                actual_value=actual_value,
                threshold=expected,
                severity=rule.get("severity", "MEDIUM"),
                recommended_action=rule.get("recommended_action", "QUALITY_REVIEW")
            )
        )
        result["risk_score"] += rule.get("risk_score", 0)
        _update_decision(
            result,
            status=rule.get("status", "WARNING"),
            severity=rule.get("severity", "MEDIUM"),
            action=rule.get("recommended_action", "QUALITY_REVIEW")
        )
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="boolean_equals",
            field=field,
            actual_value=actual_value,
            expected=expected,
            outcome="triggered"
        )
    else:
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="boolean_equals",
            field=field,
            actual_value=actual_value,
            expected=expected,
            outcome="passed"
        )


def _check_numeric_gt(rule: dict, payload: dict, result: dict):
    field = rule.get("field")
    threshold = rule.get("threshold")
    rule_id = rule.get("rule_id", "unknown_rule")

    if field not in payload or payload.get(field) is None:
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="numeric_gt",
            field=field,
            actual_value=None,
            expected=threshold,
            outcome="skipped_missing_field"
        )
        return

    actual_value = payload.get(field)

    if actual_value > threshold:
        result["issues"].append(
            _build_issue(
                code=rule.get("issue_code"),
                field=field,
                actual_value=actual_value,
                threshold=threshold,
                severity=rule.get("severity", "MEDIUM"),
                recommended_action=rule.get("recommended_action", "QUALITY_REVIEW")
            )
        )
        result["risk_score"] += rule.get("risk_score", 0)
        _update_decision(
            result,
            status=rule.get("status", "WARNING"),
            severity=rule.get("severity", "MEDIUM"),
            action=rule.get("recommended_action", "QUALITY_REVIEW")
        )
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="numeric_gt",
            field=field,
            actual_value=actual_value,
            expected=threshold,
            outcome="triggered"
        )
    else:
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="numeric_gt",
            field=field,
            actual_value=actual_value,
            expected=threshold,
            outcome="passed"
        )


def _check_numeric_lt(rule: dict, payload: dict, result: dict):
    field = rule.get("field")
    threshold = rule.get("threshold")
    rule_id = rule.get("rule_id", "unknown_rule")

    if field not in payload or payload.get(field) is None:
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="numeric_lt",
            field=field,
            actual_value=None,
            expected=threshold,
            outcome="skipped_missing_field"
        )
        return

    actual_value = payload.get(field)

    if actual_value < threshold:
        result["issues"].append(
            _build_issue(
                code=rule.get("issue_code"),
                field=field,
                actual_value=actual_value,
                threshold=threshold,
                severity=rule.get("severity", "MEDIUM"),
                recommended_action=rule.get("recommended_action", "QUALITY_REVIEW")
            )
        )
        result["risk_score"] += rule.get("risk_score", 0)
        _update_decision(
            result,
            status=rule.get("status", "WARNING"),
            severity=rule.get("severity", "MEDIUM"),
            action=rule.get("recommended_action", "QUALITY_REVIEW")
        )
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="numeric_lt",
            field=field,
            actual_value=actual_value,
            expected=threshold,
            outcome="triggered"
        )
    else:
        _add_audit(
            result,
            rule_id=rule_id,
            rule_type="numeric_lt",
            field=field,
            actual_value=actual_value,
            expected=threshold,
            outcome="passed"
        )


def run(module_config: dict, payload: dict):
    rules = module_config.get("rules", {})
    actions = rules.get("actions", {})

    result = {
        "status": "APPROVED",
        "risk_score": 0,
        "issues": [],
        "audit": [],
        "severity": "LOW",
        "recommended_action": actions.get("APPROVED", "RELEASE_BATCH")
    }

    _check_required_fields(rules, payload, result)

    checks = rules.get("checks", [])

    for rule in checks:
        rule_type = rule.get("type")

        if rule_type == "boolean_equals":
            _check_boolean_equals(rule, payload, result)

        elif rule_type == "numeric_gt":
            _check_numeric_gt(rule, payload, result)

        elif rule_type == "numeric_lt":
            _check_numeric_lt(rule, payload, result)

    return result
