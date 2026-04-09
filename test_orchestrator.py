from src.regulatory.service import simulate_regulatory_change_detection
from src.sentinel.orchestrator import process_deltas

client_records = [
    {
        "client_id": "CLIENT-001",
        "jurisdiction": "EU",
        "domain": "pharma",
        "monitored_rules": {
            "temperature_warning_high": 8,
            "temperature_critical_high": 25,
            "gmp_required": True
        },
        "entities": ["BATCH-001", "DOSSIER-001"]
    },
    {
        "client_id": "CLIENT-002",
        "jurisdiction": "EU",
        "domain": "food",
        "monitored_rules": {
            "temperature_warning_high": 8
        },
        "entities": ["LOT-FOOD-001"]
    }
]

deltas = simulate_regulatory_change_detection()
result = process_deltas(deltas, client_records)

print(result)
