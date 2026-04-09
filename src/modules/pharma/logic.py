from src.core.rule_engine import evaluate_rules
from src.core.explainer import build_explanation
from src.modules.pharma.policy import apply_policy


def _normalize_pharma_rules(module_config: dict) -> list:

    # FIX: se arriva come stringa (errore loader), converti in dict
    if isinstance(module_config, str):
        import json
        module_config = json.loads(module_config)

    rules_config = module_config.get("rules", {}).get("rules", {})
    selected_frameworks = module_config.get("selected_frameworks", []) or []

    normalized_rules = []

    # Se non viene passato nulla, usa tutti i framework disponibili
    frameworks_to_use = (
        selected_frameworks if selected_frameworks else list(rules_config.keys())
    )

    for framework_name in frameworks_to_use:
        framework_rules = rules_config.get(framework_name, {})

        if not framework_rules:
            continue

        # REQUIRED FIELDS
        for field in framework_rules.get("required_fields", []):
            normalized_rules.append({
                "rule_id": f"{framework_name.lower()}_required_{field}",
                "rule_type": "required_field",
                "field": field,
                "expected": "required",
                "severity": "HIGH",
                "recommended_action": "HOLD_BATCH",
                "framework": framework_name
            })

        # CHECKS
        for rule in framework_rules.get("checks", []):
            normalized_rules.append({
                "rule_id": rule.get("rule_id"),
                "rule_type": rule.get("type"),
                "field": rule.get("field"),
                "expected": rule.get("threshold", rule.get("expected")),
                "severity": rule.get("severity", "LOW"),
                "recommended_action": rule.get("recommended_action", "RELEASE_BATCH"),
                "status": rule.get("status", "APPROVED"),
                "risk_score": rule.get("risk_score", 0),
                "issue_code": rule.get("issue_code", rule.get("rule_id")),
                "framework": framework_name
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
    if isinstance(module_config, str):
        import json
        module_config = json.loads(module_config)

    normalized_rules = _normalize_pharma_rules(module_config)
    compliance_scope = module_config.get("compliance_scope", {})
    engine_result = evaluate_rules(payload, normalized_rules)

    # BASE RESULT (contratto API stabile)
    result = {
        "risk_score": 0,
        "issues": [],
        "audit": engine_result.get("audit", []),
        "severity": "LOW",
        "recommended_action": "RELEASE_BATCH",
        "decision_code": "PHARMA_APPROVED",
        "review_required": False,
        "regulatory_impact": "LOW",
        "batch_disposition": "RELEASED",
        "compliance_scope": compliance_scope
    }

    # BUILD ISSUES + RISK
    for rule in normalized_rules:
        rule_id = rule.get("rule_id")

        triggered = any(
            item.get("rule_id") == rule_id and item.get("outcome") in ["failed", "triggered"]
            for item in engine_result.get("audit", [])
        )

        if not triggered:
            continue

        issue = {
            "code": rule.get("issue_code", rule_id),
            "field": rule.get("field"),
            "actual_value": payload.get(rule.get("field")),
            "threshold": rule.get("expected"),
            "severity": rule.get("severity", "LOW"),
            "recommended_action": rule.get("recommended_action", "RELEASE_BATCH"),
            "framework": rule.get("framework")
        }

        result["issues"].append(issue)
        result["risk_score"] += rule.get("risk_score", 0)

    # DECISION LOGIC (SOLO SEVERITY)
    blocking_issues = [
        i for i in result["issues"]
        if i.get("severity") == "HIGH"
    ]

    if blocking_issues:
        result["severity"] = "HIGH"
        result["recommended_action"] = "HOLD_BATCH"
        result["decision_code"] = "PHARMA_REJECTED"
        result["review_required"] = True
        result["regulatory_impact"] = "HIGH"
        result["batch_disposition"] = "QUARANTINED"

    elif any(i.get("severity") == "MEDIUM" for i in result["issues"]):
        result["severity"] = "MEDIUM"
        result["recommended_action"] = "QUALITY_REVIEW"
        result["decision_code"] = "PHARMA_REVIEW"
        result["review_required"] = True
        result["regulatory_impact"] = "MEDIUM"
        result["batch_disposition"] = "ON_HOLD"

    else:
        result["severity"] = "LOW"
        result["recommended_action"] = "RELEASE_BATCH"
        result["decision_code"] = "PHARMA_APPROVED"
        result["review_required"] = False
        result["regulatory_impact"] = "LOW"
        result["batch_disposition"] = "RELEASED"

    # STATUS + OUTPUT
    if result["severity"] == "HIGH":
        result["status"] = "REJECTED"
        result["output_type"] = "NOT_APPROVED"
        result["execution_allowed"] = False

    elif result["severity"] == "MEDIUM":
        result["status"] = "REVIEW"
        result["output_type"] = "RISK_DOSSIER"
        result["execution_allowed"] = False

    else:
        result["status"] = "APPROVED"
        result["output_type"] = "AUDIT_READY"
        result["execution_allowed"] = True

    # EXPLANATION
    result["explanation"] = build_explanation(result)

    # PAYLOAD TRACE
    result["payload_received"] = payload

    return result
