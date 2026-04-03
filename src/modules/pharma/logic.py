def run(module_config: dict, payload: dict):

    rules = module_config.get("rules", {})
    risk_weights = module_config.get("rules", {}).get("risk_weights", {})
    actions = module_config.get("rules", {}).get("actions", {})

    result = {
        "status": "APPROVED",
        "risk_score": 0,
        "issues": [],
        "severity": "LOW",
        "recommended_action": actions.get("APPROVED")
    }

    temp_rules = rules.get("temperature", {})
    temp = payload.get("temperature")

    if temp is not None:

        critical_max = temp_rules.get("critical_max")
        critical_min = temp_rules.get("critical_min")

        if critical_max is not None and temp > critical_max:
            result["status"] = "CRITICAL"
            result["severity"] = "CRITICAL"
            result["risk_score"] = risk_weights.get("temperature_critical", 0)
            result["issues"].append("temperature_critical_high")
            result["recommended_action"] = actions.get("CRITICAL")

        elif critical_min is not None and temp < critical_min:
            result["status"] = "CRITICAL"
            result["severity"] = "CRITICAL"
            result["risk_score"] = risk_weights.get("temperature_critical", 0)
            result["issues"].append("temperature_critical_low")
            result["recommended_action"] = actions.get("CRITICAL")

    return result
