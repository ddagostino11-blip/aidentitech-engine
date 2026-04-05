from datetime import datetime
from typing import List, Dict, Any

from src.regulatory.models import RegulatoryDelta, ClientImpactAlert


def _priority_from_delta(delta: RegulatoryDelta) -> str:
    if delta.impact_level == "CRITICAL":
        return "CRITICAL"
    if delta.impact_level == "HIGH":
        return "HIGH"
    if delta.impact_level == "MEDIUM":
        return "MEDIUM"
    return "LOW"


def _build_message(client_id: str, rule_id: str, old_value: Any, new_value: Any) -> str:
    return (
        f"Client '{client_id}' may be impacted by regulatory change on rule "
        f"'{rule_id}': previous value '{old_value}' → new value '{new_value}'."
    )


def detect_client_impacts(
    delta: RegulatoryDelta,
    client_records: List[Dict[str, Any]]
) -> List[ClientImpactAlert]:
    alerts: List[ClientImpactAlert] = []

    for record in client_records:
        client_id = record.get("client_id")
        jurisdiction = record.get("jurisdiction")
        domain = record.get("domain")
        monitored_rules = record.get("monitored_rules", {})

        if jurisdiction != delta.jurisdiction:
            continue

        if domain != delta.domain:
            continue

        if delta.rule_id not in monitored_rules:
            continue

        client_value = monitored_rules.get(delta.rule_id)

        impacted = False

        if isinstance(delta.old_value, (int, float)) and isinstance(delta.new_value, (int, float)):
            if isinstance(client_value, (int, float)):
                if delta.new_value < delta.old_value and client_value > delta.new_value:
                    impacted = True
                elif delta.new_value > delta.old_value and client_value < delta.new_value:
                    impacted = True
        else:
            if client_value != delta.new_value:
                impacted = True

        if not impacted:
            continue

        alert = ClientImpactAlert(
            alert_id=f"alert-{client_id}-{delta.delta_id}",
            client_id=client_id,
            delta_id=delta.delta_id,
            domain=delta.domain,
            jurisdiction=delta.jurisdiction,
            priority=_priority_from_delta(delta),
            alert_type="REGULATORY_IMPACT",
            created_at=datetime.utcnow(),
            message=_build_message(
                client_id=client_id,
                rule_id=delta.rule_id,
                old_value=delta.old_value,
                new_value=delta.new_value
            ),
            recommended_action="REVIEW_COMPLIANCE_IMMEDIATELY",
            impacted_entities=record.get("entities", [])
        )
        alerts.append(alert)

    return alerts


def serialize_impact_alerts(alerts: List[ClientImpactAlert]) -> List[Dict[str, Any]]:
    serialized = []

    for alert in alerts:
        serialized.append({
            "alert_id": alert.alert_id,
            "client_id": alert.client_id,
            "delta_id": alert.delta_id,
            "domain": alert.domain,
            "jurisdiction": alert.jurisdiction,
            "priority": alert.priority,
            "alert_type": alert.alert_type,
            "created_at": alert.created_at.isoformat(),
            "message": alert.message,
            "recommended_action": alert.recommended_action,
            "impacted_entities": alert.impacted_entities
        })

    return serialized
