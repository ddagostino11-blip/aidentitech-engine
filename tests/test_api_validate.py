from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_api_approved():
    payload = {
        "module": "pharma",
        "client_id": "TEST-OK",
        "payload": {
            "product_id": "P-OK-001",
            "batch": "B-OK-001",
            "gmp_compliant": True,
            "temperature": 5
        }
    }

    response = client.post("/validate", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "APPROVED"
    assert data["decision_code"] == "PHARMA_APPROVED"


def test_api_review():
    payload = {
        "module": "pharma",
        "client_id": "TEST-REV",
        "payload": {
            "product_id": "P-REV-001",
            "batch": "B-REV-001",
            "gmp_compliant": True,
            "temperature": 12
        }
    }

    response = client.post("/validate", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "REVIEW"
    assert data["decision_code"] == "PHARMA_REVIEW"


def test_api_rejected():
    payload = {
        "module": "pharma",
        "client_id": "TEST-FAIL",
        "payload": {
            "product_id": "P-FAIL-001",
            "batch": "B-FAIL-001",
            "gmp_compliant": False,
            "temperature": 5
        }
    }

    response = client.post("/validate", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "REJECTED"
    assert data["decision_code"] == "PHARMA_REJECTED"
