import json


def load_config(path="risk_config.json"):
    with open(path, "r") as f:
        return json.load(f)


def compute_risk(features: dict, config: dict):
    score = 0
    reasons = []

    weights = config["weights"]

    for key, active in features.items():
        if active and key in weights:
            score += weights[key]
            reasons.append(key)

    return score, reasons


def check_hard_block(features: dict, config: dict):
    for flag in config.get("hard_block_flags", []):
        if features.get(flag):
            return True
    return False


def classify(score: int, hard_block: bool, config: dict):
    if hard_block:
        return "BLOCK"

    thresholds = config["thresholds"]

    if score <= thresholds["certified_max"]:
        return "CERTIFIED"
    elif score <= thresholds["risk_max"]:
        return "RISK"
    else:
        return "BLOCK"


def recommended_action(status: str, reasons: list):
    if status == "BLOCK":
        if "missing_data" in reasons:
            return "REQUEST_MISSING_DATA"
        return "STOP_PROCESSING"

    if status == "RISK":
        if "legal_review_required" in reasons:
            return "ESCALATE_TO_LEGAL"
        return "GENERATE_RISK_REPORT"

    if status == "CERTIFIED":
        return "EMIT_DOSSIER"

    return "UNKNOWN"


def evaluate(features: dict):
    config = load_config()

    score, reasons = compute_risk(features, config)
    hard_block = check_hard_block(features, config)
    status = classify(score, hard_block, config)
    action = recommended_action(status, reasons)

    return {
        "risk_score": score,
        "status": status,
        "hard_block": hard_block,
        "reasons": reasons,
        "recommended_action": action
    }


if __name__ == "__main__":
    test_features = {
        "missing_data": False,
        "regulatory_ambiguity": True,
        "fiscal_inconsistency": False,
        "market_mismatch": True,
        "low_confidence_source": False,
        "legal_review_required": False,
        "policy_transition_active": False,
        "signature_or_timestamp_missing": False
    }

    result = evaluate(test_features)
    print(json.dumps(result, indent=2))
