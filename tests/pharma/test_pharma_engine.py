from src.modules.pharma.logic import run
from src.modules.pharma.config import load_config


def test_pharma_approved():
    config = load_config()

    payload = {
        "product_id": "P-OK-001",
        "batch": "B-OK-001",
        "gmp_compliant": True,
        "temperature": 5
    }

    result = run(config, payload)

    assert result["status"] == "APPROVED"
    assert result["severity"] == "LOW"
    assert result["decision_code"] == "PHARMA_APPROVED"


def test_pharma_review():
    config = load_config()

    payload = {
        "product_id": "P-REV-001",
        "batch": "B-REV-001",
        "gmp_compliant": True,
        "temperature": 12
    }

    result = run(config, payload)

    assert result["status"] == "REVIEW"
    assert result["severity"] == "MEDIUM"
    assert result["decision_code"] == "PHARMA_REVIEW"


def test_pharma_rejected():
    config = load_config()

    payload = {
        "product_id": "P-FAIL-001",
        "batch": "B-FAIL-001",
        "gmp_compliant": False,
        "temperature": 5
    }

    result = run(config, payload)

    assert result["status"] == "REJECTED"
    assert result["severity"] == "HIGH"
    assert result["decision_code"] == "PHARMA_REJECTED"
