from src.sentinel.logger import SentinelLogger


class DecisionEngine:
    def execute(self, module, input_data, policy):
        validation_result = module.validate(input_data)

        if not validation_result["valid"]:
            return self._build_output(
                status="REJECTED",
                reason="VALIDATION_FAILED",
                details=validation_result
            )

        decision_result = module.decide(input_data)

        if "status" in decision_result:
            status = decision_result["status"]
        else:
            status = self._apply_policy(decision_result, policy)

        integrity_result = module.integrity(input_data)

        if not integrity_result["ok"]:
            return self._build_output(
                status="CRITICAL_ERROR",
                reason="INTEGRITY_FAILED",
                details=integrity_result
            )

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

    def _build_output(self, status, **kwargs):
        return {
            "status": status,
            **kwargs
        }
