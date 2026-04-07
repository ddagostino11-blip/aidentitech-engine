from src.sentinel.logger import SentinelLogger


class DecisionEngine:

    def execute(self, module, input_data, policy):

        # 1. VALIDAZIONE
        validation_result = module.validate(input_data)

        if not validation_result["valid"]:
            return self._build_output(
                status="REJECTED",
                reason="VALIDATION_FAILED",
                details=validation_result
            )

        # 2. DECISIONE
        decision_result = module.decide(input_data)

        # 3. POLICY (modulo-aware)
        if "status" in decision_result:
            status = decision_result["status"]
        else:
            status = self._apply_policy(decision_result, policy)

        # 4. INTEGRITÀ
        integrity_result = module.integrity(input_data)

        if not integrity_result["ok"]:
            return self._build_output(
                status="CRITICAL_ERROR",
                reason="INTEGRITY_FAILED",
                details=integrity_result
            )

        # 5. OUTPUT + SENTINEL
        output = self._build_output(
            status=status,
            decision=decision_result,
            integrity=integrity_result
        )

        logger = SentinelLogger()
        logger.log(output)

        return output

    def _apply_policy(self, decision_result, policy):
        severity = decision_result.get("severity", "LOW")

        if severity == "HIGH":
            return "REJECTED"

        if severity == "MEDIUM":
            return "REVIEW"

        return "APPROVED"

    def _build_output(self, status, decision=None, integrity=None, reason=None, details=None):
        from datetime import datetime

        # output base (compatibilità)
        output = {
            "status": status,
            "decision": decision,
            "integrity": integrity,
            "reason": reason,
            "details": details
        }

        # se non c'è decision (validation fail ecc.)
        if not decision:
            return output

        # decision context globale
        decision_context = {
            "module": decision.get("module_name", "unknown"),
            "module_version": decision.get("module_version", "v1"),
            "normalized_input_hash": decision.get("normalized_input_hash"),

            "regulatory_context": {
                "regulatory_version": decision.get("regulatory_version", "unknown"),
                "policy_version": decision.get("policy_version", "unknown"),
                "rule_version": decision.get("rule_version", "unknown"),
                "jurisdiction": {
                    "country": decision.get("jurisdiction_country"),
                    "region": decision.get("jurisdiction_region"),
                    "authority": decision.get("regulatory_authority"),
                    "market_scope": decision.get("market_scope")
                }
            },

            "localization": {
                "site": {
                    "country": decision.get("site_country"),
                    "region": decision.get("site_region"),
                    "city": decision.get("site_city"),
                    "facility_id": decision.get("facility_id")
                },
                "target_market": {
                    "country": decision.get("target_market_country"),
                    "region": decision.get("target_market_region"),
                    "scope": decision.get("target_market_scope")
                },
                "customer_entity": {
                    "country": decision.get("customer_entity_country"),
                    "region": decision.get("customer_entity_region")
                }
            },

            "decision_summary": {
                "decision_code": decision.get("decision_code"),
                "severity": decision.get("severity"),
                "status": status,
                "regulatory_impact": decision.get("regulatory_impact")
            },

            "trace": {
                "timestamp": datetime.utcnow().isoformat(),
                "engine_version": decision.get("engine_version", "v1")
            }
        }

        # aggancio immutabilità (se presente)
        if integrity:
            decision_context["immutability"] = {
                "hash": integrity.get("hash"),
                "prev_hash": integrity.get("prev_hash"),
                "signature": integrity.get("signature")
            }

        # attach finale
        output["decision_context"] = decision_context

        return output
