from src.core.rule_engine import evaluate_rules
from src.core.explainer import build_explanation
from src.modules.pharma.policy import apply_policy


REGULATORY_IMPACT_MAP = {
    "LOW": "LOW",
    "MEDIUM": "MEDIUM",
    "HIGH": "HIGH",
    "CRITICAL": "HIGH",
}


DECISION_PRESETS = {
    "approved": {
        "status": "APPROVED",
        "recommended_action": "RELEASE_BATCH",
        "decision_code": "PHARMA_APPROVED",
        "review_required": False,
        "batch_disposition": "RELEASED",
    },
    "medium_review": {
        "status": "REVIEW",
        "recommended_action": "QUALITY_REVIEW",
        "decision_code": "PHARMA_WARNING",
        "review_required": True,
        "batch_disposition": "ON_HOLD",
    },
    "medium_high_risk_review": {
        "status": "REVIEW",
        "recommended_action": "QUALITY_REVIEW",
        "decision_code": "PHARMA_HIGH_RISK_REVIEW",
        "review_required": True,
        "batch_disposition": "QUARANTINED",
    },
    "medium_multi_warning": {
        "status": "REVIEW",
        "recommended_action": "QUALITY_REVIEW",
        "decision_code": "PHARMA_MULTI_WARNING",
        "review_required": True,
        "batch_disposition": "QUARANTINED",
    },
    "high_reject": {
        "status": "REJECTED",
        "recommended_action": "HOLD_BATCH",
        "decision_code": "PHARMA_HIGH_RISK_REJECT",
        "review_required": True,
        "batch_disposition": "QUARANTINED",
    },
    "critical_reject": {
        "status": "CRITICAL",
        "recommended_action": "BLOCK_AND_ESCALATE",
        "decision_code": "PHARMA_CRITICAL_REJECT",
        "review_required": True,
        "batch_disposition": "BLOCKED",
    },
    "review_required_fallback": {
        "status": "REVIEW",
        "recommended_action": "QUALITY_REVIEW",
        "decision_code": "PHARMA_REVIEW_REQUIRED",
        "review_required": True,
        "batch_disposition": "ON_HOLD",
    },
}


def _regulatory_impact_from_severity(severity: str) -> str:
    return REGULATORY_IMPACT_MAP.get(severity, "LOW")


def _apply_preset(result: dict, preset_name: str):
    preset = DECISION_PRESETS[preset_name]
    result.update(preset)


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


def _build_base_result(engine_result: dict, compliance_scope: dict) -> dict:
    result = {
        "status": "APPROVED",
        "risk_score": engine_result.get("risk_score", 0),
        "issues": engine_result.get("issues", []),
        "primary_issue": engine_result.get("primary_issue"),
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
    return result


def _apply_severity_outcome(result: dict):
    max_severity = result.get("severity", "LOW")
    medium_issues = [
        issue for issue in result.get("issues", [])
        if issue.get("severity") == "MEDIUM"
    ]

    if max_severity == "CRITICAL":
        _apply_preset(result, "critical_reject")
        return

    if max_severity == "HIGH":
        _apply_preset(result, "high_reject")
        return

    if max_severity == "MEDIUM":
        if result.get("risk_score", 0) >= 75:
            _apply_preset(result, "medium_high_risk_review")
        elif len(medium_issues) >= 2:
            _apply_preset(result, "medium_multi_warning")
        else:
            _apply_preset(result, "medium_review")
        return

    _apply_preset(result, "approved")


def _apply_decision_guardrails(result: dict, max_severity: str) -> dict:
    if result.get("status") == "APPROVED" and max_severity in {"MEDIUM", "HIGH", "CRITICAL"}:
        _apply_preset(result, "review_required_fallback")
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

    result = _build_base_result(engine_result, compliance_scope)
    result["issues"] = normalized_issues
    result["primary_issue"] = primary_issue

    max_severity = result["severity"]

    blocking_issues = [
        issue for issue in result["issues"]
        if issue.get("severity") in {"HIGH", "CRITICAL"}
    ]
    result["blocking_issues_count"] = len(blocking_issues)
    result["regulatory_impact"] = _regulatory_impact_from_severity(max_severity)

    _apply_severity_outcome(result)

    if primary_issue and max_severity in {"HIGH", "CRITICAL"}:
        result["recommended_action"] = primary_issue.get(
            "recommended_action",
            result["recommended_action"],
        )

    result = apply_policy(result, module_config, payload)
    result = _apply_decision_guardrails(result, max_severity)
    result["explanation"] = build_explanation(result)

    return result
