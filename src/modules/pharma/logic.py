def run(module_config: dict, payload: dict):
    result = {
        "status": "APPROVED",
        "risk_score": 0,
        "issues": [],
        "severity": "LOW",
        "recommended_action": "RELEASE_BATCH"
    }

    temp = payload.get("temperature")

    if temp is not None:
        if temp > 30:
            result["status"] = "CRITICAL"
            result["severity"] = "CRITICAL"
            result["risk_score"] = 80
            result["issues"].append("temperature_critical_out_of_range")
            result["recommended_action"] = "BLOCK_AND_ESCALATE"

    return result
