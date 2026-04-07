from src.modules.pharma.logic import run


class PharmaAdapter:
    def __init__(self, module_config: dict):
        self.module_config = module_config

    def validate(self, data: dict):
        """
        Validazione minima input-level.
        La logica dettagliata resta nel modulo pharma.
        """
        required_fields = ["product_id", "batch", "gmp_compliant", "temperature"]
        missing = [f for f in required_fields if f not in data]

        if missing:
            return {
                "valid": False,
                "missing_fields": missing
            }

        return {"valid": True}

    def decide(self, data: dict):
        """
        Usa la logica pharma reale e traduce il risultato
        nel formato atteso dal core.
        """
        result = run(self.module_config, data)

        return {
            "severity": result.get("severity", "LOW"),
            "reason": result.get("decision_code", "PHARMA_UNKNOWN"),
            "module_result": result,
        }

    def integrity(self, data: dict):
        """
        Per ora pharma non usa ancora un layer di integrity
        forte come Shield. Quindi passa sempre.
        """
        return {"ok": True}
