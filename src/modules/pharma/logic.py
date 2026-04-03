from src.core.rule_engine import evaluate_rules
from src.core.explainer import build_explanation


def _normalize_pharma_rules(module_config: dict) -> list:
    rules = module_config.get("rules", {})

    normalized_rules = []

    for field in rules.get("required_fields", []):
        normalized_rules.append({
            "rule_id": f"required_{field}",
            "rule_type": "required_field",
            "field": field,
            "expected": "required",
            "severity": "HIGH",
            "recommended_action": "HOLD_BATCH"
        })

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


def _status_rank(status: str) -> int:
    ranking = {
        "APPROVED": 1,
        "WARNING": 2,
        "REJECTED": 3,
        "CRITICAL": 4
    }
    return ranking.get(status, 0)


def _action_rank(action: str) -> int:
    ranking = {
        "RELEASE_BATCH": 1,
        "QUALITY_REVIEW": 2,
        "HOLD_BATCH": 3,
        "BLOCK_AND_ESCALATE": 4
    }
    return ranking.get(action, 0)


def run(module_config: dict, payload: dict):
    normalized_rules = _normalize_pharma_rules(module_config)
    engine_result = evaluate_rules(payload, normalized_rules)

    result = {
        "status": "APPROVED",
        "risk_score": 0,
        "issues": [],
        "audit": engine_result.get("audit", []),
        "severity": "LOW",
        "recommended_action": "RELEASE_BATCH"
    }

    for rule in normalized_rules:
        rule_id = rule.get("rule_id")
        triggered = any(
            item.get("rule_id") == rule_id and item.get("outcome") in ["failed", "triggered"]
            for item in engine_result.get("audit", [])
        )

        if not triggered:
            continue

        result["issues"].append({
            "code": rule.get("issue_code", rule_id),
            "field": rule.get("field"),
            "actual_value": payload.get(rule.get("field")),
            "threshold": rule.get("expected"),
            "severity": rule.get("severity", "LOW"),
            "recommended_action": rule.get("recommended_action", "RELEASE_BATCH")
        })

        result["risk_score"] += rule.get("risk_score", 0)

        if _status_rank(rule.get("status", "APPROVED")) > _status_rank(result["status"]):
            result["status"] = rule.get("status", "APPROVED")

        if _severity_rank(rule.get("severity", "LOW")) > _severity_rank(result["severity"]):
            result["severity"] = rule.get("severity", "LOW")

        if _action_rank(rule.get("recommended_action", "RELEASE_BATCH")) > _action_rank(result["recommended_action"]):
            result["recommended_action"] = rule.get("recommended_action", "RELEASE_BATCH")

    result["explanation"] = build_explanation(result)

    return result
