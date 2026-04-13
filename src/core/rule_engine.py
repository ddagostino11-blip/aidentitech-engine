from typing import Any, Dict, List


SEVERITY_ORDER = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def _severity_rank(severity: str) -> int:
    return SEVERITY_ORDER.get(severity, 0)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _evaluate_range_rule(
    actual_value: Any,
    min_inclusive: Any = None,
    max_inclusive: Any = None,
    min_exclusive: Any = None,
    max_exclusive: Any = None,
) -> bool:
    if not _is_number(actual_value):
        return False

    if min_inclusive is not None and actual_value < min_inclusive:
        return False
    if min_exclusive is not None and actual_value <= min_exclusive:
        return False
    if max_inclusive is not None and actual_value > max_inclusive:
        return False
    if max_exclusive is not None and actual_value >= max_exclusive:
        return False

    return True


def _evaluate_comparison_rule(
    actual_value: Any,
    operator: str | None,
    violation_value: Any = None,
    threshold: Any = None,
    min_inclusive: Any = None,
    max_inclusive: Any = None,
    min_exclusive: Any = None,
    max_exclusive: Any = None,
) -> bool:
    if operator == "equals":
        return actual_value == violation_value

    if operator == "gt":
        return (
            actual_value is not None
            and threshold is not None
            and _is_number(actual_value)
            and _is_number(threshold)
            and actual_value > threshold
        )

    if operator == "gte":
        return (
            actual_value is not None
            and threshold is not None
            and _is_number(actual_value)
            and _is_number(threshold)
            and actual_value >= threshold
        )

    if operator == "lt":
        return (
            actual_value is not None
            and threshold is not None
            and _is_number(actual_value)
            and _is_number(threshold)
            and actual_value < threshold
        )

    if operator == "lte":
        return (
            actual_value is not None
            and threshold is not None
            and _is_number(actual_value)
            and _is_number(threshold)
            and actual_value <= threshold
        )

    if operator == "range":
        return _evaluate_range_rule(
            actual_value=actual_value,
            min_inclusive=min_inclusive,
            max_inclusive=max_inclusive,
            min_exclusive=min_exclusive,
            max_exclusive=max_exclusive,
        )

    return False


def _deduplicate_issues_by_group(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected: Dict[str, Dict[str, Any]] = {}

    for issue in issues:
        group = issue.get("group")
        if not group:
            selected[f"__ungrouped__:{issue.get('rule_id')}"] = issue
            continue

        current = selected.get(group)
        if current is None:
            selected[group] = issue
            continue

        current_rank = _severity_rank(current.get("severity", "LOW"))
        candidate_rank = _severity_rank(issue.get("severity", "LOW"))

        if candidate_rank > current_rank:
            selected[group] = issue
            continue

        if candidate_rank == current_rank:
            current_priority = current.get("priority", 0)
            candidate_priority = issue.get("priority", 0)

            if candidate_priority > current_priority:
                selected[group] = issue

    return list(selected.values())


def _select_primary_issue(issues: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    if not issues:
        return None

    return max(
        issues,
        key=lambda issue: (
            _severity_rank(issue.get("severity", "LOW")),
            issue.get("priority", 0),
            issue.get("risk_score", 0),
        ),
    )


def _normalize_risk_score(issues: List[Dict[str, Any]]) -> int:
    if not issues:
        return 0

    primary_issue = _select_primary_issue(issues)
    max_severity = primary_issue.get("severity", "LOW") if primary_issue else "LOW"

    base_by_severity = {
        "LOW": 10,
        "MEDIUM": 40,
        "HIGH": 70,
        "CRITICAL": 85,
    }

    base_score = base_by_severity.get(max_severity, 0)

    issue_pressure = min(len(issues) * 5, 15)

    additional_risk = sum(
        min(int(issue.get("risk_score", 0) * 0.15), 10)
        for issue in issues
        if issue is not primary_issue
    )
    additional_risk = min(additional_risk, 20)

    critical_bonus = 0
    if max_severity == "CRITICAL" and len(issues) > 1:
        critical_bonus = 5

    normalized = base_score + issue_pressure + additional_risk + critical_bonus
    return min(normalized, 100)


def evaluate_rules(payload: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    raw_issues: List[Dict[str, Any]] = []
    audit: List[Dict[str, Any]] = []

    for rule in rules:
        rule_id = rule.get("rule_id")
        rule_type = rule.get("rule_type")
        field = rule.get("field")

        actual_value = payload.get(field)

        outcome = "passed"
        triggered = False

        operator = rule.get("operator")
        violation_value = rule.get("violation_value")
        threshold = rule.get("threshold")
        group = rule.get("group")
        priority = rule.get("priority", 0)

        min_inclusive = rule.get("min_inclusive")
        max_inclusive = rule.get("max_inclusive")
        min_exclusive = rule.get("min_exclusive")
        max_exclusive = rule.get("max_exclusive")

        if rule_type == "required_field":
            if actual_value is None:
                outcome = "failed"
                triggered = True

        elif rule_type == "comparison_rule":
            triggered = _evaluate_comparison_rule(
                actual_value=actual_value,
                operator=operator,
                violation_value=violation_value,
                threshold=threshold,
                min_inclusive=min_inclusive,
                max_inclusive=max_inclusive,
                min_exclusive=min_exclusive,
                max_exclusive=max_exclusive,
            )
            outcome = "triggered" if triggered else "passed"

        else:
            outcome = "unsupported_rule_type"

        audit.append(
            {
                "rule_id": rule_id,
                "rule_type": rule_type,
                "field": field,
                "actual_value": actual_value,
                "group": group,
                "priority": priority,
                "operator": operator,
                "violation_value": violation_value,
                "threshold": threshold,
                "min_inclusive": min_inclusive,
                "max_inclusive": max_inclusive,
                "min_exclusive": min_exclusive,
                "max_exclusive": max_exclusive,
                "outcome": outcome,
            }
        )

        if triggered:
            severity = rule.get("severity", "LOW")
            recommended_action = rule.get("recommended_action", "QUALITY_REVIEW")
            issue_code = rule.get("issue_code", rule_id)
            issue_status = rule.get("status", "APPROVED")

            raw_issues.append(
                {
                    "code": issue_code,
                    "field": field,
                    "actual_value": actual_value,
                    "group": group,
                    "priority": priority,
                    "operator": operator,
                    "violation_value": violation_value,
                    "threshold": threshold,
                    "min_inclusive": min_inclusive,
                    "max_inclusive": max_inclusive,
                    "min_exclusive": min_exclusive,
                    "max_exclusive": max_exclusive,
                    "severity": severity,
                    "recommended_action": recommended_action,
                    "risk_score": rule.get("risk_score", 0),
                    "status": issue_status,
                    "rule_id": rule_id,
                    "rule_type": rule_type,
                }
            )

    issues = _deduplicate_issues_by_group(raw_issues)
    primary_issue = _select_primary_issue(issues)

    max_severity = primary_issue.get("severity", "LOW") if primary_issue else "LOW"
    normalized_risk_score = _normalize_risk_score(issues)

    return {
        "severity": max_severity,
        "risk_score": normalized_risk_score,
        "issues": issues,
        "audit": audit,
        "primary_issue": primary_issue,
    }
