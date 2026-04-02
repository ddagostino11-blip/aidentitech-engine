from core.verify_ledger import verify_ledger
from core.verify_ledger_signature import main as verify_signature
from cli.run_validation import run_validation


def _derive_severity(status: str) -> str:
    mapping = {
        "APPROVED": "LOW",
        "WARNING": "MEDIUM",
        "REJECTED": "HIGH",
        "CRITICAL": "CRITICAL"
    }
    return mapping.get(status, "UNKNOWN")


def pharma_logic(module_config: dict, payload: dict):
    rules = module_config.get("rules", {})
    weights = rules.get("risk_weights", {})
    actions = rules.get("actions", {})
    temperature_rules = rules.get(
        "temperature",
        {"min": 2, "max": 8, "critical_min": 0, "critical_max": 25}
    )

    issues = []
    risk_score = 0
    status = "APPROVED"

    required_fields = rules.get("required_fields", [])
    for field in required_fields:
        if field not in payload:
            issues.append(f"missing_{field}")
            risk_score += weights.get("missing_field", 25)

    if issues:
        status = "REJECTED"

    if not payload.get("gmp_compliant", False):
        issues.append("gmp_non_compliant")
        risk_score += weights.get("gmp_non_compliant", 60)
        status = "REJECTED"

    temp = payload.get("temperature")
    if temp is not None:
        if temp < temperature_rules["critical_min"] or temp > temperature_rules["critical_max"]:
            issues.append("temperature_critical_out_of_range")
            risk_score += weights.get("temperature_critical", 80)
            status = "CRITICAL"
        elif temp < temperature_rules["min"] or temp > temperature_rules["max"]:
            issues.append("temperature_out_of_range")
            risk_score += weights.get("temperature_warning", 20)
            if status not in ("REJECTED", "CRITICAL"):
                status = "WARNING"

    severity = _derive_severity(status)
    recommended_action = actions.get(status, "MANUAL_REVIEW")

    return {
        "status": status,
        "severity": severity,
        "risk_score": risk_score,
        "issues": issues,
        "recommended_action": recommended_action
    }


def execute_validation(config: dict, module_config: dict, module_name: str, payload: dict | None = None):
    run_validation(
        config,
        module_config,
        verify_ledger,
        verify_signature
    )

    payload = payload or {}

    if module_name == "pharma":
        decision = pharma_logic(module_config, payload)
    else:
        decision = {
            "status": "APPROVED",
            "severity": "LOW",
            "risk_score": 0,
            "issues": [],
            "recommended_action": "NO_ACTION"
        }

    return {
        "module": module_name,
        "decision": decision,
        "payload_received": payload
    }
