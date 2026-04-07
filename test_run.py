from src.core.decision_engine import DecisionEngine
from src.modules.pharma.adapter import PharmaAdapter

# mock config (semplificato)
module_config = {
    "rules": {
        "required_fields": ["product_id", "batch", "gmp_compliant", "temperature"],
        "checks": []
    },
    "compliance_scope": {
        "region": "EU"
    }
}

# payload test (OK)
payload = {
    "product_id": "P001",
    "batch": "BATCH001",
    "gmp_compliant": True,
    "temperature": 5
}

engine = DecisionEngine()
module = PharmaAdapter(module_config)

result = engine.execute(module, payload, policy={})

print(result)
