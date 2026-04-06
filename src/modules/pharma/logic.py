from src.core.rule_engine import evaluate_rules
from src.core.explainer import build_explanation
from src.modules.pharma.policy import apply_policy

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
    compliance_scope = module_config.get("compliance_scope", {})

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

    # Collect issues
    for issue in engine_result.get("issues", []):
        result["issues"].append(issue)
        result["risk_score"] += issue.get("risk_score", 0)

    # Aggregation logic
    if result["issues"]:
        max_severity = max(
            result["issues"],
            key=lambda x: _severity_rank(x.get("severity", "LOW"))
        )["severity"]
    else:
        max_severity = "LOW"

    result["severity"] = max_severity
    result["blocking_issues_count"] = len([
        i for i in result["issues"] if i.get("severity") == "HIGH"
    ])

    if max_severity == "HIGH":
        result["status"] = "REJECTED"
        result["recommended_action"] = "HOLD_BATCH"
        result["decision_code"] = "PHARMA_REJECTED"
        result["review_required"] = True
        result["regulatory_impact"] = "HIGH"
        result["batch_disposition"] = "QUARANTINED"

    # Explanation + payload
    result["explanation"] = build_explanation(result)
    result["payload_received"] = payload

    # 👉 POLICY LAYER (NUOVO)
    result = apply_policy(result, module_config, payload)

    return result
