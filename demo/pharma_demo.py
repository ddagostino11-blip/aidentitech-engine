import requests

BASE_URL = "http://127.0.0.1:8000"


def run_demo():
    print("\n--- PHARMA REGULATORY DEMO ---\n")

    # 👉 INPUT SEMPLICE
    client_id = input("Client ID: ") or "CLIENT_A"
    product_id = input("Product ID: ") or "PROD_TEST_01"
    batch = input("Batch: ") or "BATCH_001"
    temperature = float(input("Temperature: ") or 15)
    gmp_input = input("GMP compliant? (yes/no): ") or "no"

    gmp_compliant = gmp_input.lower() in ["yes", "y"]

    print("\n[1] Sending validation request...")

    validate_payload = {
        "client_id": client_id,
        "product_id": product_id,
        "module": "pharma",
        "payload": {
            "product_id": product_id,
            "batch": batch,
            "gmp_compliant": gmp_compliant,
            "temperature": temperature,
        }
    }

    response = requests.post(f"{BASE_URL}/validate", json=validate_payload)
    data = response.json()

    if response.status_code != 200:
        print("❌ Validation failed:", data)
        return

    event_id = data.get("legal_event_id")

    if not event_id:
        print("❌ No event generated")
        return

    print(f"[2] Regulatory event created: {event_id}")

    print("\n[3] Fetching current events...")

    events = requests.get(f"{BASE_URL}/legal/events").json()

    print(f"Total events: {events.get('count')}")

    print("\n[4] Submitting legal decision...")

    decision_payload = {
        "event_id": event_id,
        "decision": "approve",
        "reviewer_name": "LEGAL_TEAM",
        "notes": "approved via demo"
    }

    decision_response = requests.post(
        f"{BASE_URL}/legal/decision",
        json=decision_payload
    )

    decision_data = decision_response.json()

    if decision_response.status_code != 200:
        print("❌ Decision failed:", decision_data)
        return

    print("[5] Event approved and processed")

    print("\n[6] Fetching audit trail...")

    audit = requests.get(
        f"{BASE_URL}/legal/events/{event_id}/audit"
    ).json()

    print("\n--- AUDIT TRAIL ---")

    for step in audit.get("steps", []):
        print(
            f"- {step.get('action')} by {step.get('actor')} at {step.get('timestamp')}"
        )

    print("\n--- DEMO COMPLETE ---\n")


if __name__ == "__main__":
    run_demo()
