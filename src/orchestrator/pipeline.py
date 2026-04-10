from typing import Dict, Any, List
from fastapi import HTTPException

from src.modules.registry import AVAILABLE_MODULES
from src.services.event_store import create_regulatory_event, find_open_event


def run_validation_pipeline(
    client_id: str,
    product_id: str,
    module: str,
    payload: Dict[str, Any],
    frameworks: List[str],
    load_config_fn,
    load_module_config_fn,
    execute_validation_fn,
    append_ledger_entry_fn,
) -> Dict[str, Any]:
    # 1) Guard rail modulo
    if module not in AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail=f"Modulo non valido: {module}")

    if not AVAILABLE_MODULES[module]["enabled"]:
        raise HTTPException(status_code=400, detail=f"Modulo disabilitato: {module}")

    # 2) Config
    config = load_config_fn()
    module_config = load_module_config_fn(module)

    # 3) Framework selezionati dal client
    module_config["selected_frameworks"] = frameworks or []

    # 4) Esecuzione validation reale
    result = execute_validation_fn(
        config=config,
        module_config=module_config,
        module_name=module,
        payload=payload,
    )

    decision = result.get("decision", {})

    # 5) Legal flag
    legal_required = decision.get("review_required", False)
    decision["legal_flag"] = bool(legal_required)

    # 6) Se serve legal review, crea o riusa evento
    created_event = None
    reused_event = None

    if legal_required:
        reused_event = find_open_event(
            client_id=client_id,
            product_id=product_id,
            domain=module,
            status="pending_legal_review",
        )

        if reused_event is None:
            severity = decision.get("severity", "MEDIUM")
            regulatory_impact = decision.get("regulatory_impact", "MEDIUM")
            decision_code = decision.get("decision_code", "validation_review_required")

            created_event = create_regulatory_event(
                domain=module,
                rule_id=decision_code,
                change_type="validation_review_required",
                impact_level=regulatory_impact,
                priority=severity,
                impacts_detected=len(decision.get("issues", [])),
                freeze_active=True,
                freeze_reason="auto_regulatory_high_impact",
                legal_tasks=[
                    {
                        "review_id": f"{client_id}-{product_id}-{module}",
                        "status": "pending_review",
                        "priority": severity,
                    }
                ],
                extra_fields={
                    "client_id": client_id,
                    "product_id": product_id,
                    "source": "validation_pipeline",
                    "decision_snapshot": {
                        "status": decision.get("status"),
                        "severity": decision.get("severity"),
                        "recommended_action": decision.get("recommended_action"),
                        "review_required": legal_required,
                    },
                },
            )

    # 7) Ledger
    ledger_entry = append_ledger_entry_fn({
        "client_id": client_id,
        "product_id": product_id,
        "module": module,
        "decision": decision.get("status"),
    })

    # 8) Evento finale usato in output
    legal_event = created_event or reused_event

    # 9) Output
    return {
        "engine": "aidentitech",
        "module": module,

        "client_id": client_id,
        "product_id": product_id,
        "decision_trace_id": ledger_entry.get("hash"),

        "output_type": decision.get("output_type"),
        "execution_allowed": decision.get("execution_allowed"),

        "status": decision.get("status"),
        "severity": decision.get("severity"),
        "risk_score": decision.get("risk_score"),
        "recommended_action": decision.get("recommended_action"),

        "decision_code": decision.get("decision_code"),
        "review_required": legal_required,
        "legal_flag": decision.get("legal_flag"),

        "blocking_issues_count": decision.get("blocking_issues_count", 0),
        "regulatory_impact": decision.get("regulatory_impact"),
        "batch_disposition": decision.get("batch_disposition"),

        "issues": decision.get("issues", []),
        "audit": decision.get("audit", []),
        "explanation": decision.get("explanation", {}),

        "payload_received": result.get("payload_received", {}),
        "versioning": result.get("versioning", module_config.get("versioning", {})),
        "compliance_scope": decision.get("compliance_scope", {}),

        "legal_event_created": created_event is not None,
        "legal_event_reused": reused_event is not None,
        "legal_event_id": legal_event.get("event_id") if legal_event else None,

        "ledger_hash": ledger_entry.get("hash"),
    }
